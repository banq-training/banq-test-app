/* Photo Studio: check a learner's photo, change it with the workshop's Foundry picture models, and save
 * the new pictures they like into the page's own gallery.
 *
 * The page never holds a credential: it posts a photo and a few words to the Website preview, and this
 * module signs in as the workshop identity (see assistant.cjs) with an Entra ID token, never an API key.
 * A vision model checks the photo before the change and the new picture after it, so people, documents
 * and screens are politely refused. Only pictures made here can be saved, and only inside site/.
 * It starts no processes, servers, or ports.
 *
 * Messages from the page, and the replies it gets back:
 *   { type: 'workshop.photo.edit', id, image, prompt } -> { type: 'workshop.photo.result', id, ok, image, model }
 *   { type: 'workshop.photo.save', id, image, title }  -> { type: 'workshop.photo.saved', id, ok, file }
 * A reply with ok: false has an error in plain words, plus refused: true when the studio turned a picture down. */
const crypto = require('node:crypto')
const fs = require('node:fs')
const path = require('node:path')
const { createSignIn, readSettings } = require('./assistant.cjs')

const CHECK_MODELS = ['gpt-5.6-luna', 'gpt-5.5']
const EDIT_MODELS = ['gpt-image-2', 'FLUX.1-Kontext-pro', 'gpt-image-1.5']
const API_VERSION = '2025-04-01-preview'
const MAX_PHOTO_BYTES = 4 * 1024 * 1024
const MAX_SAVE_BYTES = 2 * 1024 * 1024 // published websites allow 2 MiB per file
const MAX_PROMPT = 300
const MAX_TITLE = 60
const PER_MINUTE = 6
const PER_HOUR = 40
const REMEMBERED = 30
const MAX_ITEMS = 24
const CHECK_INSTRUCTIONS = [
  "You check photos for a beginners' photo editor. It may only edit pictures of things, places and animals.",
  'Set allowed to false if the photo shows any person or part of a person (face, hands, body), a document,',
  'paper or whiteboard with writing, a screen showing content, an ID badge or card, or a vehicle number plate.',
  'Otherwise set allowed to true. Give a short, friendly reason.',
].join(' ')
const CHECK_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['allowed', 'reason'],
  properties: { allowed: { type: 'boolean' }, reason: { type: 'string' } },
}
const GUIDANCE = ' Keep it friendly and fictional. Do not add people, faces, words, letters, logos or brands.'
// A 400 answer that mentions any of these means the model's safety system blocked the request.
const SAFETY_WORDS = /content[ _-]?(policy|filter)|moderation|safety/i
const DATA_URL = /^data:(image\/(?:jpeg|png|webp));base64,([A-Za-z0-9+/]+={0,2})$/
const PNG_SIGNATURE = Buffer.from('89504e470d0a1a0a', 'hex')
const NOT_READY = 'The photo helper is not switched on in this Codespace yet. Ask a helper.'
const CHECK_BUSY = 'The photo check is busy right now. Please try again in a moment.'
const RESULT_REFUSED = "The new picture showed something this studio can't keep, so it was not kept. Try different words."
const ONLY_MADE_HERE = 'Only pictures made here can be saved to the gallery.'

/** A problem explained in plain words for the learner; `refused` marks a picture the studio turned down. */
class PhotoError extends Error {
  constructor(message, refused = false) {
    super(message)
    this.refused = refused
  }
}

/** Name a picture's type from its first bytes (its "magic bytes"), or return null for anything else. */
function pictureKind(bytes) {
  if (bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return { mime: 'image/jpeg', extension: '.jpg' }
  if (bytes.subarray(0, 8).equals(PNG_SIGNATURE)) return { mime: 'image/png', extension: '.png' }
  if (bytes.toString('latin1', 0, 4) === 'RIFF' && bytes.toString('latin1', 8, 12) === 'WEBP') {
    return { mime: 'image/webp', extension: '.webp' }
  }
  return null
}

/** Decode a picture the page sent as a data URL. Returns { bytes, mime, extension }, or null unless it is a
 * JPEG, PNG or WebP picture of at most maxBytes whose first bytes match the type it claims to be. */
function decodePicture(value, maxBytes) {
  // Check the length first, so a huge message is turned away before any decoding.
  if (typeof value !== 'string' || value.length > 32 + Math.ceil(maxBytes / 3) * 4) return null
  const match = DATA_URL.exec(value)
  if (!match) return null
  const bytes = Buffer.from(match[2], 'base64')
  const kind = pictureKind(bytes)
  if (!kind || kind.mime !== match[1] || bytes.length > maxBytes) return null
  return { bytes, ...kind }
}

function toDataUrl(picture) {
  return `data:${picture.mime};base64,${picture.bytes.toString('base64')}`
}

function fingerprint(bytes) {
  return crypto.createHash('sha256').update(bytes).digest('hex')
}

/** Text from the page with spaces, line breaks and control characters collapsed; anything else becomes ''. */
function cleanText(value) {
  return typeof value === 'string' ? value.replace(/[\s\u0000-\u001f\u007f]+/g, ' ').trim() : ''
}

/** The { allowed, reason } answer inside a Responses API reply, or null when the reply is not in that shape. */
function readVerdict(text) {
  try {
    const answer = JSON.parse(text).output
      .filter(item => item.type === 'message')
      .flatMap(item => item.content || [])
      .filter(part => part.type === 'output_text')
      .map(part => part.text)
      .join('')
    const verdict = JSON.parse(answer)
    return typeof verdict.allowed === 'boolean' && typeof verdict.reason === 'string' ? verdict : null
  } catch {
    return null
  }
}

/** The new picture inside an images/edits reply, or null when it is missing, not a picture, or too large to save. */
function readEditedPicture(text) {
  try {
    const bytes = Buffer.from(JSON.parse(text).data[0].b64_json, 'base64')
    const kind = pictureKind(bytes)
    return kind && bytes.length <= MAX_SAVE_BYTES ? { bytes, ...kind } : null
  } catch {
    return null
  }
}

/** A file-name-safe version of the title: lowercase letters, digits and dashes, at most 40 characters. */
function slug(title) {
  const dashed = title.normalize('NFKD').toLowerCase().replace(/[^a-z0-9]+/g, '-')
  return dashed.slice(0, 40).replace(/^-+|-+$/g, '') || 'picture'
}

/** A short, sortable UTC timestamp such as 20261019-124634. */
function stamp(date) {
  return date.toISOString().slice(0, 19).replace(/[-:]/g, '').replace('T', '-')
}

/** The real path of an existing folder, with any links followed, or null. */
function realFolder(folder) {
  try {
    const real = fs.realpathSync(folder)
    return fs.statSync(real).isDirectory() ? real : null
  } catch {
    return null
  }
}

/** True when `child` is `parent` itself or somewhere inside it. */
function isInside(parent, child) {
  const relative = path.relative(parent, child)
  return relative === '' || (relative !== '..' && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative))
}

/** Return <page>/<name>, creating it when missing; refuses a link (or a file) in its place. */
function ordinaryFolder(page, name) {
  const folder = path.join(page, name)
  try {
    fs.mkdirSync(folder)
  } catch (error) {
    if (error.code !== 'EEXIST') throw error
  }
  const info = fs.lstatSync(folder)
  if (info.isSymbolicLink() || !info.isDirectory()) {
    throw new PhotoError(`The ${name} folder next to the page must be an ordinary folder, not a link.`)
  }
  return folder
}

/** Read data/gallery.json. A missing or unreadable list starts again as { items: [] }; other keys are kept. */
function readList(file) {
  let info
  try {
    info = fs.lstatSync(file)
  } catch (error) {
    if (error.code === 'ENOENT') return { items: [] }
    throw error
  }
  if (info.isSymbolicLink() || !info.isFile()) throw new PhotoError('data/gallery.json must be an ordinary file, not a link.')
  let list
  try {
    list = JSON.parse(fs.readFileSync(file, 'utf8'))
  } catch {
    return { items: [] } // not valid JSON, so the page cannot read it either
  }
  if (!list || typeof list !== 'object' || Array.isArray(list)) return { items: [] }
  if (!Array.isArray(list.items)) list.items = []
  return list
}

/** Write the picture under a new name, adding -2, -3 and so on when needed. The 'wx' flag never replaces
 * an existing file and never follows a link. Returns the file name. */
function writeNewPicture(folder, base, picture) {
  for (let number = 1; number <= 99; number++) {
    const name = number === 1 ? `${base}${picture.extension}` : `${base}-${number}${picture.extension}`
    try {
      fs.writeFileSync(path.join(folder, name), picture.bytes, { flag: 'wx' })
      return name
    } catch (error) {
      if (error.code !== 'EEXIST') throw error
    }
  }
  throw new PhotoError('There are already many pictures with this title. Try another title.')
}

/** Write the list as a new file beside the old one, then swap it in: the page never reads half a list,
 * and a link put in its place is replaced rather than followed. */
function writeList(file, list) {
  const partial = path.join(path.dirname(file), `.gallery-${crypto.randomUUID()}.partial`)
  fs.writeFileSync(partial, `${JSON.stringify(list, null, 2)}\n`, { flag: 'wx' })
  fs.renameSync(partial, file)
}

/** Save the picture as <page>/gallery/<name> and list it first in <page>/data/gallery.json.
 * Everything is checked before anything is written. Returns 'gallery/<name>'. */
function saveToGallery({ pageDirectory, siteDirectory }, picture, title, created) {
  const site = realFolder(siteDirectory)
  const page = realFolder(pageDirectory)
  if (!site || !page || !isInside(site, page)) throw new PhotoError('Pictures can only be saved inside the site folder.')
  const gallery = ordinaryFolder(page, 'gallery')
  const listFile = path.join(ordinaryFolder(page, 'data'), 'gallery.json')
  const list = readList(listFile)
  const file = `gallery/${writeNewPicture(gallery, `${slug(title)}-${stamp(created)}`, picture)}`
  list.items = [{ file, title, created: created.toISOString() }, ...list.items].slice(0, MAX_ITEMS)
  writeList(listFile, list)
  return file
}

/** Create the preview's photo handler, with its own sign-in, limits and memory of the pictures it made.
 * settings, loadSettings, fetchImpl, now and both time limits (in milliseconds) are injectable for tests. */
function createPhotoHandler({
  settings = null, loadSettings = readSettings, fetchImpl = globalThis.fetch, now = Date.now,
  checkTimeout = 30000, editTimeout = 120000,
} = {}) {
  let current = settings
  let busy = false
  const started = [] // when each recent edit started, oldest first
  const made = [] // { hash, saved } for the last REMEMBERED pictures made here, oldest first
  const token = createSignIn({ fetchImpl, now, name: 'The photo helper' })

  /** POST with a time limit that also covers reading the answer. Status 0 means no answer arrived in time. */
  async function post(url, headers, body, milliseconds) {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), milliseconds)
    try {
      const response = await fetchImpl(url, { method: 'POST', headers, body, signal: controller.signal })
      return { status: response.status, text: await response.text() }
    } catch {
      return { status: 0, text: '' }
    } finally {
      clearTimeout(timer)
    }
  }

  /** A token for the workshop identity; the sign-in messages are already in plain words. */
  async function signIn() {
    try {
      return await token(current)
    } catch (error) {
      throw new PhotoError(error.message)
    }
  }

  /** Count this edit, or refuse it when there have been too many this minute or this hour. */
  function takeTurn() {
    while (started.length && now() - started[0] >= 3600000) started.shift()
    if (started.filter(time => now() - time < 60000).length >= PER_MINUTE) {
      throw new PhotoError('That was a lot of photos. Wait a minute and try again.')
    }
    if (started.length >= PER_HOUR) {
      throw new PhotoError('You have changed a lot of photos this hour. Take a break and try again later.')
    }
    started.push(now())
  }

  /** Ask a vision model whether the picture may be used. It fails closed: when no model answers, it throws. */
  async function checkPicture(picture, bearer) {
    const headers = { Authorization: `Bearer ${bearer}`, 'Content-Type': 'application/json' }
    const content = [
      { type: 'input_text', text: 'Check this photo.' },
      { type: 'input_image', image_url: toDataUrl(picture) },
    ]
    let denied = 0
    for (const model of CHECK_MODELS) {
      const body = JSON.stringify({
        model,
        instructions: CHECK_INSTRUCTIONS,
        input: [{ role: 'user', content }],
        text: { format: { type: 'json_schema', name: 'photo_check', schema: CHECK_SCHEMA, strict: true } },
        reasoning: { effort: 'low' },
        max_output_tokens: 300,
      })
      const answer = await post(`https://${current.FOUNDRY_RESOURCE}.openai.azure.com/openai/v1/responses`, headers, body, checkTimeout)
      if (answer.status === 401 || answer.status === 403) denied++
      const verdict = answer.status === 200 ? readVerdict(answer.text) : null
      if (verdict) return verdict
    }
    throw new PhotoError(denied === CHECK_MODELS.length ? 'The photo helper is not allowed to use the photo check. Ask a helper.' : CHECK_BUSY)
  }

  /** Change the photo with the first model that can. A content-safety refusal stops at once. */
  async function changePhoto(photo, prompt, bearer) {
    let denied = 0
    for (const model of EDIT_MODELS) {
      const gptImage = model.startsWith('gpt-image')
      const form = new FormData()
      form.append('model', model)
      form.append('prompt', prompt + GUIDANCE)
      form.append('n', '1')
      if (gptImage) {
        form.append('quality', 'low')
        form.append('output_format', 'jpeg')
      }
      form.append('image', new Blob([photo.bytes], { type: photo.mime }), `photo${photo.extension}`)
      const url = gptImage
        ? `https://${current.FOUNDRY_RESOURCE}.openai.azure.com/openai/v1/images/edits`
        : `https://${current.FOUNDRY_RESOURCE}.services.ai.azure.com/openai/deployments/${encodeURIComponent(model)}/images/edits?api-version=${API_VERSION}`
      // No Content-Type header here: fetch writes the multipart one, with its boundary, itself.
      const answer = await post(url, { Authorization: `Bearer ${bearer}` }, form, editTimeout)
      if (answer.status === 400 && SAFETY_WORDS.test(answer.text)) {
        throw new PhotoError('The safety filter stopped this change. Try different, friendly words.', true)
      }
      if (answer.status === 401 || answer.status === 403) denied++
      const picture = answer.status === 200 ? readEditedPicture(answer.text) : null
      if (picture) return { picture, model }
      // Busy, too slow, unreachable, or an answer without a usable picture: try the next model.
    }
    throw new PhotoError(denied === EDIT_MODELS.length
      ? 'The photo helper is not allowed to use the picture models. Ask a helper.'
      : 'The picture models are busy right now. Please try again in a moment.')
  }

  /** Check the photo, change it, check the new picture, and reply with it. */
  async function edit(message) {
    const reply = { type: 'workshop.photo.result', id: message.id }
    if (busy) return { ...reply, ok: false, error: 'Still working on your last photo.' }
    busy = true
    try {
      const photo = decodePicture(message.image, MAX_PHOTO_BYTES)
      if (!photo) throw new PhotoError('Choose a JPEG, PNG or WebP photo under 4 MB.')
      const prompt = cleanText(message.prompt)
      if (!prompt) throw new PhotoError('Describe the change in a few words first.')
      if (prompt.length > MAX_PROMPT) throw new PhotoError(`Keep the description to ${MAX_PROMPT} characters or fewer.`)
      // Codespaces can deliver the secrets after the preview has started, so look again until they arrive.
      current = current || loadSettings()
      if (!current) throw new PhotoError(NOT_READY)
      takeTurn()
      const bearer = await signIn()
      const before = await checkPicture(photo, bearer)
      if (!before.allowed) {
        const reason = cleanText(before.reason).slice(0, 200)
        throw new PhotoError(reason || "This photo can't be used here. Try a photo of a thing, a place or an animal.", true)
      }
      const { picture, model } = await changePhoto(photo, prompt, bearer)
      const after = await checkPicture(picture, bearer)
      if (!after.allowed) throw new PhotoError(RESULT_REFUSED, true)
      made.push({ hash: fingerprint(picture.bytes), saved: false })
      if (made.length > REMEMBERED) made.shift()
      return { ...reply, ok: true, image: toDataUrl(picture), model }
    } catch (error) {
      if (!(error instanceof PhotoError)) return { ...reply, ok: false, error: 'Something went wrong while changing the photo. Please try again.' }
      return error.refused ? { ...reply, ok: false, refused: true, error: error.message } : { ...reply, ok: false, error: error.message }
    } finally {
      busy = false
    }
  }

  /** Save a picture made here into the page's gallery. An uploaded original can never be saved. */
  function save(message, folders) {
    const reply = { type: 'workshop.photo.saved', id: message.id }
    try {
      const title = cleanText(message.title)
      if (!title) throw new PhotoError('Give the picture a title first.')
      if (title.length > MAX_TITLE) throw new PhotoError(`Keep the title to ${MAX_TITLE} characters or fewer.`)
      const picture = decodePicture(message.image, MAX_SAVE_BYTES)
      const hash = picture ? fingerprint(picture.bytes) : ''
      const entry = made.find(item => item.hash === hash)
      if (!entry) throw new PhotoError(ONLY_MADE_HERE)
      if (entry.saved) throw new PhotoError('This picture is already in the gallery.')
      const file = saveToGallery(folders, picture, title, new Date(now()))
      entry.saved = true
      return { ...reply, ok: true, file }
    } catch (error) {
      return { ...reply, ok: false, error: error instanceof PhotoError ? error.message : 'The picture could not be saved. Ask a helper.' }
    }
  }

  /** Handle one message from the page. Returns the reply, or null for messages that are not for the studio. */
  return async function handle(message, folders = {}) {
    if (!message || typeof message.id !== 'string' || message.id.length < 1 || message.id.length > 64) return null
    if (message.type === 'workshop.photo.edit') return edit(message)
    if (message.type === 'workshop.photo.save') return save(message, folders)
    return null
  }
}

module.exports = { createPhotoHandler, CHECK_INSTRUCTIONS, CHECK_MODELS, EDIT_MODELS, GUIDANCE }
