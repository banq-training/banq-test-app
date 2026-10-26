const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const { test } = require('node:test')
const { createPhotoHandler, CHECK_INSTRUCTIONS, GUIDANCE } = require('./photo.cjs')
const { resolveEntry } = require('./controller.cjs')
const { createPreview } = require('./extension.cjs')

const SECRET = 'synthetic-client-secret-value'
const SETTINGS = {
  FOUNDRY_TENANT_ID: '00000000-0000-0000-0000-000000000001',
  FOUNDRY_CLIENT_ID: '00000000-0000-0000-0000-000000000002',
  FOUNDRY_CLIENT_SECRET: SECRET,
  FOUNDRY_RESOURCE: 'synthetic-foundry',
}
const MiB = 1024 * 1024
const CHECK_URL = 'https://synthetic-foundry.openai.azure.com/openai/v1/responses'
const GPT_IMAGE_URL = 'https://synthetic-foundry.openai.azure.com/openai/v1/images/edits'
const KONTEXT_URL = 'https://synthetic-foundry.services.ai.azure.com/openai/deployments/FLUX.1-Kontext-pro/images/edits?api-version=2025-04-01-preview'
const MORNING = Date.UTC(2026, 9, 19, 12, 46, 34)

// Pretend pictures: the right first bytes ("magic bytes") and then a label, so every picture is different.
const jpeg = label => Buffer.concat([Buffer.from([0xff, 0xd8, 0xff, 0xe0]), Buffer.from(label)])
const png = label => Buffer.concat([Buffer.from('89504e470d0a1a0a', 'hex'), Buffer.from(label)])
const webp = label => Buffer.concat([Buffer.from('RIFF'), Buffer.alloc(4), Buffer.from('WEBP'), Buffer.from(label)])
const dataUrl = (bytes, type = 'image/jpeg') => `data:${type};base64,${bytes.toString('base64')}`
const bytesOf = url => Buffer.from(url.split(',')[1], 'base64')
const PHOTO = jpeg('synthetic photo of a mug on a table')

const editMessage = (fields = {}) => ({
  type: 'workshop.photo.edit', id: 'e1', image: dataUrl(PHOTO), prompt: 'Make it a watercolour painting.', ...fields,
})
const saveMessage = (image, fields = {}) => ({ type: 'workshop.photo.save', id: 's1', image, title: 'Sunny mug', ...fields })

function json(status, body) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

/** A pretend Foundry. Each entry in checks and edits answers one call, in order: a verdict or a picture
 * (status 200), a status number, { status, body }, an Error (no network), 'hang' (no answer until the time
 * limit), or a Promise of one of these. With no entry left, checks allow the photo and edits make a new JPEG. */
function fakeFoundry({ checks = [], edits = [] } = {}) {
  const calls = []
  let results = 0
  async function fetchImpl(url, options) {
    calls.push({ url, options })
    if (url.startsWith('https://login.microsoftonline.com/')) return json(200, { access_token: 'synthetic-token', expires_in: 3600 })
    const check = url === CHECK_URL
    const next = await (check ? checks : edits).shift()
    if (next instanceof Error) throw next
    if (next === 'hang') return new Promise((resolve, reject) => options.signal.addEventListener('abort', () => reject(new Error('aborted'))))
    if (typeof next === 'number') return json(next, { error: { code: 'synthetic', message: `Synthetic status ${next}.` } })
    if (next?.status) return json(next.status, next.body)
    if (check) {
      const text = JSON.stringify(next || { allowed: true, reason: 'A friendly mug on a table.' })
      return json(200, { output: [{ type: 'reasoning', summary: [] }, { type: 'message', content: [{ type: 'output_text', text }] }] })
    }
    return json(200, { data: [{ b64_json: (next || jpeg(`synthetic result ${++results}`)).toString('base64') }] })
  }
  const foundry = () => calls.filter(call => !call.url.startsWith('https://login.'))
  return {
    calls,
    fetchImpl,
    checkCalls: () => foundry().filter(call => call.url === CHECK_URL),
    editCalls: () => foundry().filter(call => call.url !== CHECK_URL),
  }
}

/** The handler under test. Every reply is checked: no secret or token may ever reach the page. */
function studio(service, options = {}) {
  const handle = createPhotoHandler({ settings: SETTINGS, fetchImpl: service.fetchImpl, ...options })
  return async (message, folders) => {
    const reply = await handle(message, folders)
    const text = JSON.stringify(reply) ?? ''
    assert.ok(!text.includes(SECRET) && !text.includes('synthetic-token'), 'a reply must never contain a secret')
    return reply
  }
}

/** A pretend workspace whose page folder is site/studio/; removed again after the test. */
function workspace(context) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'workshop-photo-'))
  context.after(() => fs.rmSync(root, { recursive: true, force: true }))
  const siteDirectory = path.join(root, 'site')
  const pageDirectory = path.join(siteDirectory, 'studio')
  fs.mkdirSync(pageDirectory, { recursive: true })
  return { root, siteDirectory, pageDirectory }
}

test('turns away bad ids, pictures and prompts before any network call', async () => {
  const service = fakeFoundry()
  const handle = studio(service)
  for (const message of [null, 'text', {}, { type: 'other', id: 'x' }, { type: 'workshop.photo.other', id: 'x' }]) {
    assert.equal(await handle(message), null)
  }
  for (const id of ['', 'x'.repeat(65), 7, undefined]) {
    assert.equal(await handle(editMessage({ id })), null)
    assert.equal(await handle(saveMessage(dataUrl(PHOTO), { id })), null)
  }
  const pictures = [
    42,
    'not a picture',
    dataUrl(PHOTO, 'image/gif'),
    'data:image/jpeg;base64,',
    'data:image/jpeg;base64,@@@@',
    ` ${dataUrl(PHOTO)}`,
    dataUrl(PHOTO, 'image/png'), // says PNG, but its first bytes are a JPEG's
    dataUrl(Buffer.from('synthetic plain text, not a picture')),
    dataUrl(Buffer.concat([PHOTO, Buffer.alloc(4 * MiB)])), // more than 4 MiB
  ]
  for (const image of pictures) {
    assert.deepEqual(await handle(editMessage({ image })),
      { type: 'workshop.photo.result', id: 'e1', ok: false, error: 'Choose a JPEG, PNG or WebP photo under 4 MB.' })
  }
  for (const prompt of ['', '  \n\t ', 42, undefined]) {
    assert.equal((await handle(editMessage({ prompt }))).error, 'Describe the change in a few words first.')
  }
  assert.equal((await handle(editMessage({ prompt: 'x'.repeat(301) }))).error, 'Keep the description to 300 characters or fewer.')
  assert.equal(service.calls.length, 0)
})

test('accepts JPEG, PNG and WebP photos up to 4 MiB and descriptions up to 300 characters', async () => {
  const service = fakeFoundry()
  const handle = studio(service)
  const largest = Buffer.concat([PHOTO, Buffer.alloc(4 * MiB - PHOTO.length)])
  const photos = [
    [dataUrl(largest), 'photo.jpg', 'image/jpeg'],
    [dataUrl(png('synthetic PNG photo'), 'image/png'), 'photo.png', 'image/png'],
    [dataUrl(webp('synthetic WebP photo'), 'image/webp'), 'photo.webp', 'image/webp'],
  ]
  for (const [image, name, type] of photos) {
    assert.equal((await handle(editMessage({ image, prompt: `  ${'x'.repeat(300)}  ` }))).ok, true)
    const form = service.editCalls().at(-1).options.body
    assert.equal(form.get('prompt'), `${'x'.repeat(300)}${GUIDANCE}`)
    assert.equal(form.get('image').name, name)
    assert.equal(form.get('image').type, type)
  }
})

test('refuses a photo the check does not allow, with the check\'s own reason, and changes nothing', async () => {
  const reason = 'This photo shows a person. Try a photo of a thing, a place or an animal.'
  const service = fakeFoundry({ checks: [{ allowed: false, reason }] })
  assert.deepEqual(await studio(service)(editMessage()), { type: 'workshop.photo.result', id: 'e1', ok: false, refused: true, error: reason })
  assert.equal(service.editCalls().length, 0)
  const [check] = service.checkCalls()
  assert.equal(check.options.headers['Content-Type'], 'application/json')
  const body = JSON.parse(check.options.body)
  assert.equal(body.model, 'gpt-5.6-luna')
  assert.equal(body.instructions, CHECK_INSTRUCTIONS)
  assert.equal(CHECK_INSTRUCTIONS, "You check photos for a beginners' photo editor. It may only edit pictures of things, places and animals. "
    + 'Set allowed to false if the photo shows any person or part of a person (face, hands, body), a document, paper or whiteboard '
    + 'with writing, a screen showing content, an ID badge or card, or a vehicle number plate. Otherwise set allowed to true. '
    + 'Give a short, friendly reason.')
  assert.deepEqual(body.input, [{ role: 'user', content: [
    { type: 'input_text', text: 'Check this photo.' },
    { type: 'input_image', image_url: dataUrl(PHOTO) },
  ] }])
  assert.deepEqual(body.text, { format: { type: 'json_schema', name: 'photo_check', strict: true, schema: {
    type: 'object', additionalProperties: false, required: ['allowed', 'reason'],
    properties: { allowed: { type: 'boolean' }, reason: { type: 'string' } },
  } } })
  assert.deepEqual(body.reasoning, { effort: 'low' })
  assert.equal(body.max_output_tokens, 300)
  const silent = fakeFoundry({ checks: [{ allowed: false, reason: '  ' }] })
  assert.match((await studio(silent)(editMessage())).error, /a thing, a place or an animal/)
})

test('fails closed: when no check model answers, nothing is changed', async () => {
  const wrongShape = { status: 200, body: { output: [{ type: 'message', content: [{ type: 'output_text', text: '{"allowed":"yes"}' }] }] } }
  for (const checks of [[500, 429], [new Error('connection lost'), 503], ['hang', 'hang'], [{ status: 200, body: { output: [] } }, wrongShape]]) {
    const service = fakeFoundry({ checks })
    assert.deepEqual(await studio(service, { checkTimeout: 20 })(editMessage()),
      { type: 'workshop.photo.result', id: 'e1', ok: false, error: 'The photo check is busy right now. Please try again in a moment.' })
    assert.deepEqual(service.checkCalls().map(call => JSON.parse(call.options.body).model), ['gpt-5.6-luna', 'gpt-5.5'])
    assert.equal(service.editCalls().length, 0)
  }
  const denied = fakeFoundry({ checks: [403, 401] })
  assert.equal((await studio(denied)(editMessage())).error, 'The photo helper is not allowed to use the photo check. Ask a helper.')
})

test('a busy gpt-image-2 falls back to FLUX Kontext, and each model gets the right multipart form', async () => {
  const result = png('synthetic Kontext result')
  const service = fakeFoundry({ edits: [429, result] })
  assert.deepEqual(await studio(service)(editMessage()),
    { type: 'workshop.photo.result', id: 'e1', ok: true, image: dataUrl(result, 'image/png'), model: 'FLUX.1-Kontext-pro' })
  const [first, second] = service.editCalls()
  assert.equal(first.url, GPT_IMAGE_URL)
  const form = first.options.body
  assert.equal(form.get('model'), 'gpt-image-2')
  assert.equal(form.get('prompt'), 'Make it a watercolour painting. Keep it friendly and fictional. Do not add people, faces, words, letters, logos or brands.')
  assert.equal(form.get('n'), '1')
  assert.equal(form.get('quality'), 'low')
  assert.equal(form.get('output_format'), 'jpeg')
  assert.equal(form.get('image').name, 'photo.jpg')
  assert.equal(form.get('image').type, 'image/jpeg')
  assert.deepEqual(Buffer.from(await form.get('image').arrayBuffer()), PHOTO)
  assert.equal(first.options.headers['Content-Type'], undefined, 'fetch writes the multipart header with its boundary')
  // What goes over the wire: multipart/form-data with a file part called "image".
  const wire = new Response(form)
  assert.match(wire.headers.get('content-type'), /^multipart\/form-data; boundary=/)
  assert.match(await wire.text(), /name="image"; filename="photo\.jpg"\r\nContent-Type: image\/jpeg\r\n/)
  assert.equal(second.url, KONTEXT_URL)
  const kontext = second.options.body
  assert.equal(kontext.get('model'), 'FLUX.1-Kontext-pro')
  assert.equal(kontext.get('prompt'), form.get('prompt'))
  assert.equal(kontext.get('n'), '1')
  assert.equal(kontext.get('quality'), null)
  assert.equal(kontext.get('output_format'), null)
  assert.equal(kontext.get('image').name, 'photo.jpg')
  // The new picture is checked before the page sees it.
  const [, resultCheck] = service.checkCalls()
  assert.equal(JSON.parse(resultCheck.options.body).input[0].content[1].image_url, dataUrl(result, 'image/png'))
})

test('server errors, time-outs, lost connections and unusable answers fall back to the next model', async () => {
  const notAPicture = { status: 200, body: { data: [{ b64_json: Buffer.from('synthetic text, not a picture').toString('base64') }] } }
  const tooLarge = Buffer.concat([jpeg('synthetic huge result'), Buffer.alloc(2 * MiB)])
  const plainBadRequest = { status: 400, body: { error: { message: 'Synthetic: the image is too small.' } } }
  const answers = [[503, new Error('connection lost')], ['hang', 500], [notAPicture, { status: 200, body: { data: [] } }], [tooLarge, plainBadRequest]]
  for (const failures of answers) {
    const service = fakeFoundry({ edits: [...failures, jpeg('synthetic gpt-image-1.5 result')] })
    const reply = await studio(service, { editTimeout: 20 })(editMessage())
    assert.equal(reply.model, 'gpt-image-1.5')
    assert.equal(reply.image, dataUrl(jpeg('synthetic gpt-image-1.5 result')))
    const calls = service.editCalls()
    assert.deepEqual(calls.map(call => call.url), [GPT_IMAGE_URL, KONTEXT_URL, GPT_IMAGE_URL])
    assert.equal(calls[2].options.body.get('model'), 'gpt-image-1.5')
    assert.equal(calls[2].options.body.get('quality'), 'low')
    assert.equal(calls[2].options.body.get('output_format'), 'jpeg')
  }
  const busy = fakeFoundry({ edits: [429, 500, 'hang'] })
  assert.deepEqual(await studio(busy, { editTimeout: 20 })(editMessage()),
    { type: 'workshop.photo.result', id: 'e1', ok: false, error: 'The picture models are busy right now. Please try again in a moment.' })
  const denied = fakeFoundry({ edits: [403, 401, 403] })
  assert.equal((await studio(denied)(editMessage())).error, 'The photo helper is not allowed to use the picture models. Ask a helper.')
})

test('a content-safety refusal stops at once, without trying the other models', async () => {
  for (const code of ['content_policy_violation', 'moderation_blocked', 'content_filter']) {
    const service = fakeFoundry({ edits: [{ status: 400, body: { error: { code, message: 'Synthetic refusal.' } } }] })
    assert.deepEqual(await studio(service)(editMessage()), {
      type: 'workshop.photo.result', id: 'e1', ok: false, refused: true,
      error: 'The safety filter stopped this change. Try different, friendly words.',
    })
    assert.equal(service.editCalls().length, 1)
    assert.equal(service.checkCalls().length, 1, 'only the photo itself was checked')
  }
})

test('a new picture the check does not allow is not shown and cannot be saved', async context => {
  const folders = workspace(context)
  const refused = jpeg('synthetic result the check refuses')
  const service = fakeFoundry({ checks: [undefined, { allowed: false, reason: 'It shows a face.' }], edits: [refused] })
  const handle = studio(service)
  assert.deepEqual(await handle(editMessage()), {
    type: 'workshop.photo.result', id: 'e1', ok: false, refused: true,
    error: "The new picture showed something this studio can't keep, so it was not kept. Try different words.",
  })
  // When nobody can check the new picture, it is not kept either.
  const unchecked = jpeg('synthetic result nobody could check')
  const busy = fakeFoundry({ checks: [undefined, 500, 503], edits: [unchecked] })
  const handleBusy = studio(busy)
  assert.equal((await handleBusy(editMessage())).error, 'The photo check is busy right now. Please try again in a moment.')
  for (const [save, picture] of [[handle, refused], [handleBusy, unchecked]]) {
    assert.deepEqual(await save(saveMessage(dataUrl(picture)), folders),
      { type: 'workshop.photo.saved', id: 's1', ok: false, error: 'Only pictures made here can be saved to the gallery.' })
  }
  assert.deepEqual(fs.readdirSync(folders.pageDirectory), [])
})

test('one photo at a time, at most six a minute and forty an hour', async () => {
  let release
  const service = fakeFoundry({ checks: [new Promise(resolve => { release = resolve })] })
  let clock = MORNING
  const handle = studio(service, { now: () => clock })
  const first = handle(editMessage({ id: 'first' }))
  assert.deepEqual(await handle(editMessage({ id: 'second' })),
    { type: 'workshop.photo.result', id: 'second', ok: false, error: 'Still working on your last photo.' })
  release({ allowed: true, reason: 'A mug.' })
  assert.equal((await first).ok, true)
  for (let count = 2; count <= 6; count++) assert.equal((await handle(editMessage({ id: `m${count}` }))).ok, true)
  assert.equal((await handle(editMessage({ id: 'm7' }))).error, 'That was a lot of photos. Wait a minute and try again.')
  let edits = 6
  while (edits < 40) {
    if (edits % 6 === 0) clock += 61000
    assert.equal((await handle(editMessage({ id: `h${edits}` }))).ok, true)
    edits++
  }
  clock += 61000
  assert.equal((await handle(editMessage({ id: 'h41' }))).error, 'You have changed a lot of photos this hour. Take a break and try again later.')
  assert.match((await handle(editMessage({ id: 'bad', prompt: '' }))).error, /Describe/, 'turned-away messages use no turn')
  clock = MORNING + 3600000
  assert.equal((await handle(editMessage({ id: 'next-hour' }))).ok, true)
})

test('only the last 30 new pictures can be saved, each one once, and never an uploaded photo', async context => {
  const folders = workspace(context)
  let clock = MORNING
  const handle = studio(fakeFoundry(), { now: () => clock })
  const images = []
  for (let count = 0; count < 31; count++) {
    if (count && count % 6 === 0) clock += 61000
    images.push((await handle(editMessage({ id: `e${count}` }))).image)
  }
  assert.equal((await handle(saveMessage(images[0]), folders)).error, 'Only pictures made here can be saved to the gallery.')
  assert.equal((await handle(saveMessage(images[1]), folders)).ok, true)
  assert.equal((await handle(saveMessage(images[1], { id: 's2' }), folders)).error, 'This picture is already in the gallery.')
  for (const image of [dataUrl(PHOTO), 'data:image/jpeg;base64,@@@@', 42]) {
    assert.equal((await handle(saveMessage(image), folders)).error, 'Only pictures made here can be saved to the gallery.')
  }
})

test('signs in once as the workshop identity and sends a Bearer token, never an API key', async () => {
  const service = fakeFoundry()
  const handle = studio(service)
  assert.equal((await handle(editMessage({ id: 'a' }))).ok, true)
  assert.equal((await handle(editMessage({ id: 'b' }))).ok, true)
  const logins = service.calls.filter(call => call.url.startsWith('https://login.microsoftonline.com/'))
  assert.equal(logins.length, 1, 'the token is reused')
  assert.equal(logins[0].url, 'https://login.microsoftonline.com/00000000-0000-0000-0000-000000000001/oauth2/v2.0/token')
  assert.equal(logins[0].options.body.get('grant_type'), 'client_credentials')
  assert.equal(logins[0].options.body.get('scope'), 'https://cognitiveservices.azure.com/.default')
  const foundry = [...service.checkCalls(), ...service.editCalls()]
  assert.equal(foundry.length, 6)
  for (const call of foundry) {
    assert.equal(call.options.headers.Authorization, 'Bearer synthetic-token')
    assert.ok(!Object.keys(call.options.headers).some(name => name.toLowerCase() === 'api-key'))
    assert.ok(!call.url.includes('api-key') && !call.url.includes(SECRET))
  }
})

test('missing setup, failed sign-in and noisy errors give plain messages without the secret', async () => {
  let available = null
  const service = fakeFoundry()
  const handle = studio(service, { settings: null, loadSettings: () => available })
  assert.equal((await handle(editMessage())).error, 'The photo helper is not switched on in this Codespace yet. Ask a helper.')
  assert.equal(service.calls.length, 0)
  available = SETTINGS
  assert.equal((await handle(editMessage())).ok, true, 'secrets that arrive later are picked up without a reload')
  const refusing = studio({ fetchImpl: async () => json(401, { error: `synthetic refusal for ${SECRET}` }) })
  assert.equal((await refusing(editMessage())).error, 'The photo helper could not sign in. Ask a helper to check the Codespaces secrets.')
  const garbled = studio({ fetchImpl: async () => new Response(`<html>${SECRET}</html>`, { status: 200 }) })
  assert.equal((await garbled(editMessage())).error, 'The photo helper could not sign in. Ask a helper to check the Codespaces secrets.')
  const offline = studio({ fetchImpl: async () => { throw new Error(`offline ${SECRET}`) } })
  assert.equal((await offline(editMessage())).error, 'The photo helper could not reach the sign-in service. Try again in a moment.')
  const echo = { status: 400, body: { error: { message: `Synthetic bad request ${SECRET}` } } }
  assert.match((await studio(fakeFoundry({ checks: [echo, echo] }))(editMessage())).error, /photo check is busy/)
  assert.match((await studio(fakeFoundry({ edits: [echo, echo, echo] }))(editMessage())).error, /picture models are busy/)
})

test('saving writes the picture beside the page and lists it first in data/gallery.json', async context => {
  const folders = workspace(context)
  const service = fakeFoundry({ edits: [jpeg('synthetic teapot'), jpeg('synthetic second teapot'), 429, png('synthetic PNG teapot')] })
  const handle = studio(service, { now: () => MORNING })
  const made = await handle(editMessage())
  assert.deepEqual(await handle(saveMessage(made.image, { title: '  Sunny  Café\n mug! ' }), folders),
    { type: 'workshop.photo.saved', id: 's1', ok: true, file: 'gallery/sunny-cafe-mug-20261019-124634.jpg' })
  const picture = path.join(folders.pageDirectory, 'gallery', 'sunny-cafe-mug-20261019-124634.jpg')
  assert.deepEqual(fs.readFileSync(picture), bytesOf(made.image))
  const listFile = path.join(folders.pageDirectory, 'data', 'gallery.json')
  const text = fs.readFileSync(listFile, 'utf8')
  assert.deepEqual(JSON.parse(text), {
    items: [{ file: 'gallery/sunny-cafe-mug-20261019-124634.jpg', title: 'Sunny Café mug!', created: '2026-10-19T12:46:34.000Z' }],
  })
  assert.equal(text, `${JSON.stringify(JSON.parse(text), null, 2)}\n`, 'two-space JSON with a final newline')
  // Another picture with the same title in the same second gets its own name, and goes first.
  const second = await handle(editMessage({ id: 'e2' }))
  assert.equal((await handle(saveMessage(second.image, { title: 'Sunny Café mug!' }), folders)).file,
    'gallery/sunny-cafe-mug-20261019-124634-2.jpg')
  // A PNG keeps .png, and a title without letters or digits becomes "picture".
  const third = await handle(editMessage({ id: 'e3' }))
  assert.equal((await handle(saveMessage(third.image, { title: '!!!' }), folders)).file, 'gallery/picture-20261019-124634.png')
  // A long title makes a file name of at most 40 characters before the time.
  const fourth = await handle(editMessage({ id: 'e4' }))
  assert.equal((await handle(saveMessage(fourth.image, { title: 'Kitchen '.repeat(7) }), folders)).file,
    'gallery/kitchen-kitchen-kitchen-kitchen-kitchen-20261019-124634.jpg')
  assert.deepEqual(JSON.parse(fs.readFileSync(listFile, 'utf8')).items.map(item => item.file), [
    'gallery/kitchen-kitchen-kitchen-kitchen-kitchen-20261019-124634.jpg',
    'gallery/picture-20261019-124634.png',
    'gallery/sunny-cafe-mug-20261019-124634-2.jpg',
    'gallery/sunny-cafe-mug-20261019-124634.jpg',
  ])
  assert.deepEqual(fs.readdirSync(path.dirname(listFile)), ['gallery.json'], 'no half-written files are left behind')
})

test('the gallery list keeps its other keys and at most 24 items, and no picture is ever deleted', async context => {
  const folders = workspace(context)
  const gallery = path.join(folders.pageDirectory, 'gallery')
  const listFile = path.join(folders.pageDirectory, 'data', 'gallery.json')
  fs.mkdirSync(gallery)
  fs.mkdirSync(path.dirname(listFile))
  const old = Array.from({ length: 24 }, (_, index) => ({ file: `gallery/old-${index}.jpg`, title: `Old ${index}`, created: '2026-10-18T09:00:00.000Z' }))
  for (const item of old) fs.writeFileSync(path.join(folders.pageDirectory, item.file), jpeg(item.title))
  fs.writeFileSync(listFile, JSON.stringify({ heading: 'My gallery', items: old, note: 'kept' }))
  const handle = studio(fakeFoundry(), { now: () => MORNING })
  const made = await handle(editMessage())
  const { file } = await handle(saveMessage(made.image, { title: 'Blue teapot' }), folders)
  const list = JSON.parse(fs.readFileSync(listFile, 'utf8'))
  assert.deepEqual(Object.keys(list), ['heading', 'items', 'note'])
  assert.equal(list.heading, 'My gallery')
  assert.equal(list.note, 'kept')
  assert.deepEqual(list.items, [{ file, title: 'Blue teapot', created: '2026-10-19T12:46:34.000Z' }, ...old.slice(0, 23)])
  assert.equal(fs.readdirSync(gallery).length, 25, 'the oldest picture leaves the list but stays on disk')
  // A list that the page could not read either starts again; a list without items keeps its other keys.
  for (const [broken, expected] of [['{ "items": [ broken', {}], ['[1, 2, 3]', {}], ['null', {}], ['{"heading":"Mine","items":"oops"}', { heading: 'Mine' }]]) {
    fs.writeFileSync(listFile, broken)
    const next = await handle(editMessage({ id: `e${broken.length}` }))
    const saved = await handle(saveMessage(next.image, { title: 'Fresh start' }), folders)
    assert.deepEqual(JSON.parse(fs.readFileSync(listFile, 'utf8')),
      { ...expected, items: [{ file: saved.file, title: 'Fresh start', created: '2026-10-19T12:46:34.000Z' }] })
  }
})

test('saving refuses bad titles and any page folder outside site/', async context => {
  const folders = workspace(context)
  const handle = studio(fakeFoundry(), { now: () => MORNING })
  const { image } = await handle(editMessage())
  for (const title of ['', '   ', 42, undefined]) {
    assert.equal((await handle(saveMessage(image, { title }), folders)).error, 'Give the picture a title first.')
  }
  assert.equal((await handle(saveMessage(image, { title: 'x'.repeat(61) }), folders)).error, 'Keep the title to 60 characters or fewer.')
  const outside = path.join(folders.root, 'outside')
  fs.mkdirSync(outside)
  const elsewhere = [
    { ...folders, pageDirectory: outside },
    { ...folders, pageDirectory: `${folders.siteDirectory}${path.sep}..${path.sep}outside` },
    { ...folders, pageDirectory: path.join(folders.siteDirectory, 'missing') },
    { ...folders, pageDirectory: undefined },
    { ...folders, siteDirectory: undefined },
    undefined,
  ]
  for (const where of elsewhere) {
    assert.deepEqual(await handle(saveMessage(image), where),
      { type: 'workshop.photo.saved', id: 's1', ok: false, error: 'Pictures can only be saved inside the site folder.' })
  }
  assert.deepEqual(fs.readdirSync(outside), [], 'nothing was written outside site/')
  fs.writeFileSync(path.join(folders.pageDirectory, 'gallery'), 'synthetic file where the folder should be')
  assert.equal((await handle(saveMessage(image), folders)).error, 'The gallery folder next to the page must be an ordinary folder, not a link.')
  const page = { ...folders, pageDirectory: folders.siteDirectory }
  assert.equal((await handle(saveMessage(image, { title: 'x'.repeat(60) }), page)).file, `gallery/${'x'.repeat(40)}-20261019-124634.jpg`,
    'the site folder itself is a page folder too')
})

test('saving refuses linked gallery and data folders, and a page folder that links outside site/', async context => {
  const folders = workspace(context)
  const outside = path.join(folders.root, 'outside')
  const linkedGallery = path.join(folders.siteDirectory, 'linked-gallery')
  const linkedData = path.join(folders.siteDirectory, 'linked-data')
  const linkedPage = path.join(folders.siteDirectory, 'linked-page')
  for (const folder of [outside, linkedGallery, linkedData]) fs.mkdirSync(folder)
  try {
    // A junction on Windows needs no special rights; other systems make an ordinary folder symlink.
    fs.symlinkSync(outside, path.join(linkedGallery, 'gallery'), 'junction')
    fs.symlinkSync(outside, path.join(linkedData, 'data'), 'junction')
    fs.symlinkSync(outside, linkedPage, 'junction')
  } catch {
    context.skip('This computer cannot create folder links.')
    return
  }
  const handle = studio(fakeFoundry(), { now: () => MORNING })
  const { image } = await handle(editMessage())
  assert.equal((await handle(saveMessage(image), { ...folders, pageDirectory: linkedGallery })).error,
    'The gallery folder next to the page must be an ordinary folder, not a link.')
  assert.equal((await handle(saveMessage(image), { ...folders, pageDirectory: linkedData })).error,
    'The data folder next to the page must be an ordinary folder, not a link.')
  assert.equal((await handle(saveMessage(image), { ...folders, pageDirectory: linkedPage })).error,
    'Pictures can only be saved inside the site folder.')
  assert.deepEqual(fs.readdirSync(outside), [], 'nothing was written outside site/')
  assert.equal((await handle(saveMessage(image), folders)).ok, true, 'the same picture still saves beside an ordinary page')
})

test('saving refuses a linked gallery.json and writes nothing', async context => {
  const folders = workspace(context)
  const outsideList = path.join(folders.root, 'outside-list.json')
  fs.writeFileSync(outsideList, '{"items":[]}\n')
  fs.mkdirSync(path.join(folders.pageDirectory, 'data'))
  try {
    fs.symlinkSync(outsideList, path.join(folders.pageDirectory, 'data', 'gallery.json'), 'file')
  } catch {
    context.skip('This computer cannot create file links without extra rights.')
    return
  }
  const handle = studio(fakeFoundry(), { now: () => MORNING })
  const { image } = await handle(editMessage())
  assert.equal((await handle(saveMessage(image), folders)).error, 'data/gallery.json must be an ordinary file, not a link.')
  assert.equal(fs.readFileSync(outsideList, 'utf8'), '{"items":[]}\n')
  assert.deepEqual(fs.readdirSync(path.join(folders.pageDirectory, 'gallery')), [], 'the picture was not written either')
})

test('the Website preview sends photo messages to the studio and posts replies only to an open panel', async context => {
  const { root, siteDirectory } = workspace(context)
  fs.writeFileSync(path.join(siteDirectory, 'index.html'), '<html><head><title>Studio</title></head><body>Synthetic studio</body></html>')
  const posted = []
  const drawn = []
  let receive
  let dispose
  const listen = () => ({ dispose() {} })
  const panel = {
    webview: {
      cspSource: 'vscode-webview:',
      asWebviewUri: value => `webview:${value}`,
      set html(value) { drawn.push(value) },
      onDidReceiveMessage: handler => { receive = handler; return { dispose() {} } },
      postMessage: message => posted.push(message),
    },
    onDidDispose: handler => { dispose = handler; return { dispose() {} } },
  }
  const vscode = {
    workspace: {
      textDocuments: [],
      createFileSystemWatcher: () => ({ onDidChange: listen, onDidCreate: listen, onDidDelete: listen, dispose() {} }),
      onDidChangeTextDocument: listen,
      onDidSaveTextDocument: listen,
    },
    window: { createWebviewPanel: () => panel },
    Uri: { file: value => value },
    RelativePattern: class {},
    ViewColumn: { Beside: -2 },
  }
  createPreview(vscode, { workspaceState: { update() {} } }, root, resolveEntry(root))
  assert.match(drawn[0], /Synthetic studio/)
  // None of these reach the network: each one is turned away before any sign-in.
  await receive(saveMessage(dataUrl(PHOTO)))
  await receive(editMessage({ image: 'not a picture' }))
  await receive({ type: 'workshop.something-else', id: 'x' })
  assert.deepEqual(posted, [
    { type: 'workshop.photo.saved', id: 's1', ok: false, error: 'Only pictures made here can be saved to the gallery.' },
    { type: 'workshop.photo.result', id: 'e1', ok: false, error: 'Choose a JPEG, PNG or WebP photo under 4 MB.' },
  ])
  dispose()
  await receive(saveMessage(dataUrl(PHOTO), { id: 's2' }))
  assert.equal(posted.length, 2, 'nothing is posted to a closed panel')
})
