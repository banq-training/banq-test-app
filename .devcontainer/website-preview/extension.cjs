const fs = require('node:fs')
const net = require('node:net')
const path = require('node:path')
const { PreviewController, resolveEntry } = require('./controller.cjs')
const { createAssistant, createChatHandler } = require('./assistant.cjs')
const { createPhotoHandler } = require('./photo.cjs')

const VIEW_TYPE = 'workshopSite'
const ENTRY_KEY = 'workshopSite.entry'
// The owner approved Open-Meteo for the Weather starter (forecast, city search and past weather);
// everything else stays offline.
const ALLOWED_APIS = ['https://api.open-meteo.com', 'https://geocoding-api.open-meteo.com', 'https://archive-api.open-meteo.com']
const controllers = new Map()
const helpers = []
let claimTimer
let chatHandler
let photoHandler
// The "Ask my page" bubble posts questions here; answers come from the workshop's chat model.
const answerQuestion = message => {
  chatHandler = chatHandler || createChatHandler(createAssistant())
  return chatHandler(message)
}
// Photo Studio pages post photos here; photo.cjs checks and changes them, and saves pictures to the page's gallery.
const handlePhoto = (message, folders) => {
  photoHandler = photoHandler || createPhotoHandler()
  return photoHandler(message, folders)
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, character => `&#${character.charCodeAt(0)};`)
}

// A second website in site/ideas/<name>/ shares files with the first page: the kit in css/, js/,
// art/ and fonts/, and any picture or file the learner added to site/. Point any file the page
// cannot find next to itself to site/, so a missed ../../ never breaks it. The page's own data/
// folder is never redirected, so it never shows another page's entries.
function pointSharedFiles(source, pageDirectory, siteDirectory) {
  if (path.resolve(pageDirectory) === path.resolve(siteDirectory)) return source
  const shared = path.relative(pageDirectory, siteDirectory).split(path.sep).join('/')
  const sharedFile = value => {
    if (/^(?:[a-z][a-z0-9+.-]*:|\/|#|\.\.\/)/i.test(value)) return false
    const file = value.replace(/^\.\//, '').split(/[?#]/)[0]
    return Boolean(file) && !/^data\//.test(file) && !file.split('/').some(part => part === '..')
      && !fs.existsSync(path.join(pageDirectory, file)) && fs.existsSync(path.join(siteDirectory, file))
  }
  return source
    .replace(/(\s(?:src|href|poster)=")([^"]+)"/gi, (match, prefix, value) =>
      sharedFile(value) ? `${prefix}${shared}/${value.replace(/^\.\//, '')}"` : match)
    // The game imports three.js with an ES module import rather than a src attribute.
    .replace(/(\bfrom\s*|\bimport\s*\(\s*)(['"])(\.\/[^'"]+)\2/g, (match, prefix, quote, value) =>
      sharedFile(value) ? `${prefix}${quote}${shared}/${value.slice(2)}${quote}` : match)
}

function siteDirectoryOf(target) {
  const depth = path.posix.dirname(target.entry).split('/').filter(part => part && part !== '.').length
  return path.resolve(target.directory, ...Array(depth).fill('..'))
}

function renderHtml(vscode, webview, target) {
  const open = vscode.workspace.textDocuments.find(document => document.uri.fsPath === target.file)
  const source = pointSharedFiles(open ? open.getText() : fs.readFileSync(target.file, 'utf8'),
    target.directory, siteDirectoryOf(target))
  const base = `${webview.asWebviewUri(vscode.Uri.file(target.directory))}/`
  const resources = webview.cspSource
  const policy = `default-src 'none'; img-src ${resources} data:; media-src ${resources}; font-src ${resources}; style-src ${resources} 'unsafe-inline'; script-src ${resources} 'unsafe-inline'; connect-src ${resources} ${ALLOWED_APIS.join(' ')}; form-action 'none'`
  const head = `<meta http-equiv="Content-Security-Policy" content="${policy}"><base href="${base}">`
  return /<head[^>]*>/i.test(source) ? source.replace(/<head[^>]*>/i, match => match + head) : head + source
}

function createPreview(vscode, context, workspace, target, restoredPanel) {
  const site = vscode.Uri.file(path.join(workspace, 'site'))
  const options = { enableScripts: true, localResourceRoots: [site] }
  const panel = restoredPanel || vscode.window.createWebviewPanel(
    VIEW_TYPE, 'Website preview',
    // Always the second column, so the layout stays "files left, website right" and a
    // learner's open file never pushes the preview into a third, narrower column.
    { viewColumn: vscode.ViewColumn.Two, preserveFocus: true },
    { ...options, retainContextWhenHidden: true },
  )
  panel.webview.options = options
  let current = target
  let disposed = false
  let timer
  let draws = 0
  const draw = () => {
    if (disposed) return
    try {
      // A webview reloads only when its HTML text changes. Numbering each draw makes a new
      // script, picture, style or data file show too, not just edits to the page itself.
      panel.webview.html = `${renderHtml(vscode, panel.webview, current)}\n<!-- preview draw ${++draws} -->`
    } catch (error) {
      panel.webview.html = `<p style="font-family:sans-serif">Preview needs attention: ${escapeHtml(error.message)}</p>`
    }
  }
  const refresh = () => { clearTimeout(timer); timer = setTimeout(draw, 150) }
  const insideSite = uri => uri.fsPath.startsWith(site.fsPath + path.sep)
  const watcher = vscode.workspace.createFileSystemWatcher(new vscode.RelativePattern(site, '**/*'))
  const subscriptions = [
    watcher, watcher.onDidChange(refresh), watcher.onDidCreate(refresh), watcher.onDidDelete(refresh),
    vscode.workspace.onDidChangeTextDocument(event => { if (event.document.uri.fsPath === current.file) refresh() }),
    vscode.workspace.onDidSaveTextDocument(document => { if (insideSite(document.uri)) refresh() }),
    panel.webview.onDidReceiveMessage(async message => {
      const photo = typeof message?.type === 'string' && message.type.startsWith('workshop.photo.')
      const reply = photo
        ? await handlePhoto(message, { pageDirectory: current.directory, siteDirectory: path.join(workspace, 'site') })
        : await answerQuestion(message)
      if (reply && !disposed) panel.webview.postMessage(reply)
    }),
  ]
  panel.onDidDispose(() => {
    disposed = true
    clearTimeout(timer)
    for (const subscription of subscriptions) subscription.dispose()
  })
  context.workspaceState.update(ENTRY_KEY, target.entry)
  draw()
  return {
    isOpen: () => !disposed,
    entry: () => current.entry,
    async show(next) {
      current = next
      context.workspaceState.update(ENTRY_KEY, next.entry)
      // Reveal in place: moving it Beside the active group adds columns and unpins the tab,
      // so the next file a learner opens there replaces the preview.
      panel.reveal(undefined, true)
      draw()
    },
    close: () => panel.dispose(),
  }
}

function dispatch(controller, request) {
  if (!request || !['start', 'stop', 'status'].includes(request.action)) throw new Error('Use start, stop or status only.')
  if (Object.keys(request).some(key => !['action', 'entry'].includes(key))) throw new Error('Unexpected preview request field.')
  if (request.action === 'status') return controller.status()
  return controller.run(request.action, request.entry)
}

// A Codespace can run several editor windows at once: a second browser tab, a page that was
// reloaded (its old window lingers for minutes), or a window the learner never sees. Every
// window runs this helper, and the one the learner focused most recently answers site.sock.
const CLAIM_INTERVAL_MS = 3000

function ask(endpoint, request) {
  return new Promise(resolve => {
    const connection = net.createConnection(endpoint)
    let buffer = ''
    connection.setTimeout(2000, () => { connection.destroy(); resolve(null) })
    connection.once('connect', () => connection.write(JSON.stringify(request) + '\n'))
    connection.on('data', chunk => { buffer += chunk })
    connection.once('end', () => {
      try { resolve(JSON.parse(buffer.split('\n')[0]).result ?? null) } catch { resolve(null) }
    })
    connection.once('error', () => resolve(null))
  })
}

function listen(workspace, controller, output, focusedAt, startedAt = Date.now()) {
  const directory = path.join(workspace, '.workshop-preview')
  if (fs.existsSync(directory) && fs.lstatSync(directory).isSymbolicLink()) throw new Error('Preview control directory must not be a symlink.')
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 })
  const endpoint = path.join(directory, 'site.sock')
  let owned = null
  let claims = 0
  let busy = Promise.resolve()

  const handle = connection => {
    connection.setTimeout(30000, () => connection.destroy())
    let buffer = ''
    let received = false
    connection.on('error', () => {})
    connection.on('data', async chunk => {
      if (received) return
      buffer += chunk.toString()
      if (buffer.length > 8192) return connection.destroy()
      if (!buffer.includes('\n')) return
      received = true
      try {
        const request = JSON.parse(buffer.split('\n')[0])
        const result = request?.action === 'owner' && Object.keys(request).length === 1
          ? { focusedAt: focusedAt(), startedAt }
          : await dispatch(controller, request)
        connection.end(JSON.stringify({ ok: true, result }) + '\n')
      } catch (error) {
        connection.end(JSON.stringify({ ok: false, error: error.message }) + '\n')
      }
    })
  }

  const isOwner = () => {
    try { return Boolean(owned) && fs.lstatSync(endpoint).ino === owned.ino } catch { return false }
  }

  // Bind a private name, then rename it over site.sock in one step. Closing a socket deletes the
  // name it was bound to, so an older window shutting down can never remove the current one.
  async function claim() {
    if (fs.existsSync(endpoint) && !fs.lstatSync(endpoint).isSocket()) throw new Error('Preview socket path is occupied by another file.')
    const temporary = path.join(directory, `c${process.pid}-${++claims}.sock`)
    const server = net.createServer(handle)
    await new Promise((resolve, reject) => {
      server.once('error', reject)
      server.listen(temporary, resolve)
    })
    server.on('error', error => output.appendLine(error.message))
    try {
      fs.chmodSync(temporary, 0o600)
      const ino = fs.lstatSync(temporary).ino
      fs.renameSync(temporary, endpoint)
      const previous = owned
      owned = { server, ino }
      if (previous) previous.server.close()
    } catch (error) {
      server.close()
      throw error
    }
  }

  // Focus wins; between windows nobody has focused, the newer one wins, so a window left
  // behind by a reload never keeps the preview.
  async function settle() {
    if (isOwner()) return
    const owner = fs.existsSync(endpoint) ? await ask(endpoint, { action: 'owner' }) : null
    if (isOwner()) return
    const newer = owner && (focusedAt() > owner.focusedAt || (focusedAt() === owner.focusedAt && startedAt > owner.startedAt))
    if (!owner || typeof owner.focusedAt !== 'number' || newer) await claim()
  }

  return {
    settle: () => (busy = busy.then(settle, settle)),
    isOwner,
    close: () => owned?.server.close(),
  }
}

async function activate(context) {
  const vscode = require('vscode')
  if (!vscode.workspace.isTrusted) return
  const output = vscode.window.createOutputChannel('Workshop Website')
  context.subscriptions.push(output)
  let focusedAt = vscode.window.state.focused ? Date.now() : 0
  const settleAll = () => {
    for (const helper of helpers) helper.settle().catch(error => output.appendLine(error.message))
  }
  for (const folder of vscode.workspace.workspaceFolders || []) {
    const workspace = folder.uri.fsPath
    if (!fs.existsSync(path.join(workspace, '.github/skills/create-website/SKILL.md'))) continue
    const controller = new PreviewController(workspace, {
      open: target => createPreview(vscode, context, workspace, target),
    })
    controllers.set(workspace, controller)
    try { helpers.push(listen(workspace, controller, output, () => focusedAt)) } catch (error) { output.appendLine(error.message) }
  }
  settleAll()
  context.subscriptions.push(vscode.window.onDidChangeWindowState(state => {
    if (!state.focused) return
    focusedAt = Date.now()
    settleAll()
  }))
  claimTimer = setInterval(settleAll, CLAIM_INTERVAL_MS)
  claimTimer.unref?.()
  const only = () => {
    if (controllers.size === 1) return [...controllers.entries()][0]
    throw new Error('Open exactly one workshop workspace to use the website preview.')
  }
  context.subscriptions.push(vscode.window.registerWebviewPanelSerializer(VIEW_TYPE, {
    async deserializeWebviewPanel(panel) {
      try {
        const [workspace, controller] = only()
        const target = resolveEntry(workspace, context.workspaceState.get(ENTRY_KEY, 'index.html'))
        controller.preview = createPreview(vscode, context, workspace, target, panel)
      } catch { panel.dispose() }
    },
  }))
  context.subscriptions.push(vscode.commands.registerCommand('workshopSite.open', async uri => {
    try {
      const [workspace, controller] = only()
      const file = uri?.fsPath || vscode.window.activeTextEditor?.document.uri.fsPath
      const site = path.join(workspace, 'site') + path.sep
      const entry = file && file.startsWith(site) && file.endsWith('.html') ? path.relative(site, file).split(path.sep).join('/') : undefined
      await controller.run('start', entry)
    } catch (error) { vscode.window.showErrorMessage(error.message) }
  }))
  context.subscriptions.push(vscode.commands.registerCommand('workshopSite.close', async () => {
    try { await only()[1].run('stop') } catch (error) { vscode.window.showErrorMessage(error.message) }
  }))
}

async function deactivate() {
  clearInterval(claimTimer)
  for (const helper of helpers) helper.close()
  helpers.length = 0
  controllers.clear()
}

module.exports = { activate, deactivate, dispatch, renderHtml, createPreview, listen, pointSharedFiles }
