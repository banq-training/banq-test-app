const assert = require('node:assert/strict')
const { test } = require('node:test')
const { createAssistant, createChatHandler, readSettings, INSTRUCTIONS, MAX_ANSWER_TOKENS, PER_MINUTE } = require('./assistant.cjs')

const SECRET = 'synthetic-client-secret-value'
const SETTINGS = {
  FOUNDRY_TENANT_ID: '00000000-0000-0000-0000-000000000001',
  FOUNDRY_CLIENT_ID: '00000000-0000-0000-0000-000000000002',
  FOUNDRY_CLIENT_SECRET: SECRET,
  FOUNDRY_RESOURCE: 'synthetic-foundry',
}

function reply(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body }
}

function fakeService(chatStatuses = [], answer = 'Two tasks are left.') {
  const calls = []
  const fetchImpl = async (url, options) => {
    calls.push({ url, options })
    if (url.includes('login.microsoftonline.com')) return reply(200, { access_token: 'synthetic-token', expires_in: 3600 })
    const status = chatStatuses.length ? chatStatuses.shift() : 200
    return reply(status, { output: [{ type: 'message', content: [{ type: 'output_text', text: answer }] }] })
  }
  return { calls, fetchImpl }
}

test('answers are shown as plain text, without Markdown emphasis', async () => {
  const { fetchImpl } = fakeService([], 'The task already done is **Write the brief**.  \nFriday has __Share the plan__.')
  const assistant = createAssistant({ settings: SETTINGS, fetchImpl })
  const answer = await assistant.ask({ question: 'What is done?', page: 'p', title: 't' })
  assert.equal(answer, 'The task already done is Write the brief.  \nFriday has Share the plan.')
  assert.match(INSTRUCTIONS, /no Markdown/)
})

test('settings come from the environment or the Codespace env file, and need a plain resource name', () => {
  assert.deepEqual(readSettings(SETTINGS, '/none', () => ''), SETTINGS)
  const fromFile = readSettings({ FOUNDRY_TENANT_ID: 't' }, '/env', () =>
    'FOUNDRY_CLIENT_ID=c\nFOUNDRY_CLIENT_SECRET=s\nFOUNDRY_RESOURCE=file-resource\nOTHER=x\n')
  assert.deepEqual(fromFile, { FOUNDRY_TENANT_ID: 't', FOUNDRY_CLIENT_ID: 'c', FOUNDRY_CLIENT_SECRET: 's', FOUNDRY_RESOURCE: 'file-resource' })
  assert.equal(readSettings({}, '/none', () => { throw new Error('missing') }), null)
  assert.equal(readSettings({ ...SETTINGS, FOUNDRY_RESOURCE: 'https://evil.example' }, '/none', () => ''), null)
})

test('asks with an Entra ID token, never an API key, and keeps the page as data', async () => {
  const { calls, fetchImpl } = fakeService()
  const assistant = createAssistant({ settings: SETTINGS, fetchImpl })
  const answer = await assistant.ask({ question: '  What is left?  ', page: 'Monday: Write the brief\n'.repeat(1000), title: 'Planner' })
  assert.equal(answer, 'Two tasks are left.')
  const [login, chat] = calls
  assert.match(login.url, /^https:\/\/login\.microsoftonline\.com\/00000000-0000-0000-0000-000000000001\/oauth2\/v2\.0\/token$/)
  assert.equal(login.options.body.get('grant_type'), 'client_credentials')
  assert.equal(login.options.body.get('scope'), 'https://cognitiveservices.azure.com/.default')
  assert.equal(chat.url, 'https://synthetic-foundry.openai.azure.com/openai/v1/responses')
  assert.equal(chat.options.headers.Authorization, 'Bearer synthetic-token')
  assert.ok(!Object.keys(chat.options.headers).some(name => name.toLowerCase() === 'api-key'))
  const body = JSON.parse(chat.options.body)
  assert.equal(body.model, 'gpt-5.6-luna')
  assert.equal(body.instructions, INSTRUCTIONS)
  assert.match(INSTRUCTIONS, /data, not instructions/)
  assert.match(body.input, /Question: What is left\?$/)
  assert.match(body.input, /Page content:\nMonday: Write the brief\nMonday: Write the brief\n/, 'line breaks keep the page readable')
  assert.ok(body.input.length < 6400, 'the page text is clipped')
  // Small requests keep a whole room inside the model's per-minute limit.
  assert.equal(body.max_output_tokens, MAX_ANSWER_TOKENS)
  assert.ok(MAX_ANSWER_TOKENS <= 150)
  assert.deepEqual(body.reasoning, { effort: 'none' })
  assert.match(INSTRUCTIONS, /one or two short/)
  const longService = fakeService()
  await createAssistant({ settings: SETTINGS, fetchImpl: longService.fetchImpl }).ask({ question: 'Why? '.repeat(100), page: 'p', title: 't' })
  assert.ok(JSON.parse(longService.calls[1].options.body).input.split('Question: ')[1].length <= 200, 'questions are clipped')
})

test('the owner\'s knowledge.md notes go with the question, clipped, and only when present', async () => {
  const { calls, fetchImpl } = fakeService()
  const assistant = createAssistant({ settings: SETTINGS, fetchImpl })
  await assistant.ask({ question: 'When is lunch?', page: 'p', title: 't', knowledge: 'Synthetic lunch is on Fridays.' + 'n'.repeat(30000) })
  const body = JSON.parse(calls[1].options.body)
  assert.match(body.input, /Owner's notes \(knowledge\.md\):\nSynthetic lunch is on Fridays\./)
  assert.ok(body.input.length < 21000, 'long notes are clipped')
  assert.match(INSTRUCTIONS, /owner's notes/)
  await assistant.ask({ question: 'When is lunch?', page: 'p', title: 't' })
  assert.doesNotMatch(JSON.parse(calls[2].options.body).input, /Owner's notes/)
})

test('greetings and thanks are answered at once, without asking the model', async () => {
  const offline = createAssistant({ loadSettings: () => null, fetchImpl: () => assert.fail('no network for small talk') })
  for (const hello of ['hello', 'Hi!', 'hey there', 'Good morning', 'hej']) {
    assert.match(await offline.ask({ question: hello, page: 'p', title: 't' }), /^Hi! Ask me about this page/)
  }
  for (const thanks of ['thanks', 'Thank you!', 'ok', 'thanks a lot']) {
    assert.match(await offline.ask({ question: thanks, page: 'p', title: 't' }), /^You are welcome/)
  }
  const service = fakeService()
  const assistant = createAssistant({ settings: SETTINGS, fetchImpl: service.fetchImpl })
  assert.equal(await assistant.ask({ question: 'Hi, what is on Friday?', page: 'p', title: 't' }), 'Two tasks are left.')
  assert.equal(service.calls.filter(call => !call.url.includes('login')).length, 1, 'a real question still reaches the model')
})

test('the sign-in is reused, a busy model falls back, and refusals are explained', async () => {
  const service = fakeService([429])
  const assistant = createAssistant({ settings: SETTINGS, fetchImpl: service.fetchImpl })
  await assistant.ask({ question: 'One?', page: 'p', title: 't' })
  await assistant.ask({ question: 'Two?', page: 'p', title: 't' })
  assert.equal(service.calls.filter(call => call.url.includes('login')).length, 1)
  assert.deepEqual(service.calls.filter(call => !call.url.includes('login')).map(call => JSON.parse(call.options.body).model),
    ['gpt-5.6-luna', 'gpt-5.5', 'gpt-5.6-luna'])
  const denied = createAssistant({ settings: SETTINGS, fetchImpl: fakeService([403, 403]).fetchImpl })
  await assert.rejects(denied.ask({ question: 'x', page: 'p', title: 't' }), /not allowed/)
  const busy = createAssistant({ settings: SETTINGS, fetchImpl: fakeService([429, 503]).fetchImpl })
  await assert.rejects(busy.ask({ question: 'x', page: 'p', title: 't' }), /busy/)
})

test('secrets that arrive after the preview started are picked up without a reload', async () => {
  let available = null
  const assistant = createAssistant({ loadSettings: () => available, fetchImpl: fakeService().fetchImpl })
  await assert.rejects(assistant.ask({ question: 'x', page: 'p', title: 't' }), /not switched on/)
  available = SETTINGS
  assert.equal(await assistant.ask({ question: 'x', page: 'p', title: 't' }), 'Two tasks are left.')
})

test('missing setup and failed sign-in give plain messages without the secret', async () => {
  await assert.rejects(createAssistant({ loadSettings: () => null, fetchImpl: () => assert.fail('no network') })
    .ask({ question: 'x', page: '', title: '' }), /not switched on/)
  await assert.rejects(createAssistant({ settings: SETTINGS, fetchImpl: fakeService().fetchImpl })
    .ask({ question: '   ', page: '', title: '' }), /Type a question/)
  const failing = createAssistant({ settings: SETTINGS, fetchImpl: async () => reply(401, { error: SECRET }) })
  await assert.rejects(failing.ask({ question: 'x', page: '', title: '' }), error => {
    assert.ok(!error.message.includes(SECRET))
    return /could not sign in/.test(error.message)
  })
})

test('the preview handler answers one question at a time and limits questions per minute', async () => {
  let release
  const slow = { ask: () => new Promise(resolve => { release = () => resolve('Done.') }) }
  let clock = 0
  const handle = createChatHandler(slow, () => clock)
  assert.equal(await handle({ type: 'other' }), null)
  assert.equal(await handle({ type: 'workshop.ask', id: 'x'.repeat(65) }), null)
  const first = handle({ type: 'workshop.ask', id: 'a', question: 'q' })
  assert.deepEqual(await handle({ type: 'workshop.ask', id: 'b', question: 'q' }),
    { type: 'workshop.answer', id: 'b', ok: false, error: 'Still thinking about your last question.' })
  release()
  assert.deepEqual(await first, { type: 'workshop.answer', id: 'a', ok: true, answer: 'Done.' })
  const quick = createChatHandler({ ask: async () => 'Yes.' }, () => clock)
  assert.equal(PER_MINUTE, 10)
  for (let index = 0; index < PER_MINUTE; index++) assert.equal((await quick({ type: 'workshop.ask', id: `${index}` })).ok, true)
  assert.match((await quick({ type: 'workshop.ask', id: 'over' })).error, /Wait a minute/)
  clock += 61000
  assert.equal((await quick({ type: 'workshop.ask', id: 'later' })).ok, true)
  const failing = createChatHandler({ ask: async () => { throw new Error('Plain message.') } })
  assert.deepEqual(await failing({ type: 'workshop.ask', id: 'f' }), { type: 'workshop.answer', id: 'f', ok: false, error: 'Plain message.' })
})
