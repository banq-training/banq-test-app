const assert = require('node:assert/strict')
const fs = require('node:fs')
const net = require('node:net')
const os = require('node:os')
const path = require('node:path')
const { test } = require('node:test')
const { PreviewController, resolveEntry } = require('./controller.cjs')
const { dispatch, renderHtml, createPreview, listen, pointSharedFiles } = require('./extension.cjs')

const unixOnly = { skip: process.platform === 'win32' && 'Unix sockets only' }

function fixture(context) {
  const workspace = fs.mkdtempSync(path.join(os.tmpdir(), 'workshop-preview-'))
  fs.mkdirSync(path.join(workspace, 'site'))
  fs.writeFileSync(path.join(workspace, 'site/index.html'), '<html><head><title>T</title></head><body>Synthetic test</body></html>')
  context.after(() => fs.rmSync(workspace, { recursive: true, force: true }))
  const calls = []
  const operations = {
    async open(target) {
      calls.push(`open:${target.entry}`)
      let open = true
      let entry = target.entry
      return {
        isOpen: () => open,
        entry: () => entry,
        async show(next) { calls.push(`show:${next.entry}`); entry = next.entry },
        close() { calls.push('close'); open = false },
      }
    },
  }
  return { workspace, calls, operations, controller: new PreviewController(workspace, operations) }
}

test('entry paths stay inside the website and reject URLs, traversal and symlinks', context => {
  const { workspace } = fixture(context)
  assert.equal(resolveEntry(workspace).entry, 'index.html')
  for (const entry of ['../index.html', '/tmp/index.html', 'https://example.com/', '.secret.html', 'foo\\index.html', '%2e%2e/index.html', 'index.html?x=1', 'App.vue']) {
    assert.throws(() => resolveEntry(workspace, entry))
  }
  fs.symlinkSync(path.join(workspace, 'site/index.html'), path.join(workspace, 'site/linked.html'))
  assert.throws(() => resolveEntry(workspace, 'linked.html'), /symlinks/)
})

test('a missing page fails before any panel opens', async context => {
  const { controller, calls } = fixture(context)
  await assert.rejects(controller.run('start', 'missing.html'), /create-website/)
  assert.deepEqual(calls, [])
})

test('repeated start reuses the panel, stop closes it and files stay unchanged', async context => {
  const { controller, calls, workspace } = fixture(context)
  await controller.run('start')
  const again = await controller.run('start')
  assert.equal(again.reused, true)
  assert.equal(again.server, 'none')
  assert.equal(again.renderingVerified, false)
  const stopped = await controller.run('stop')
  assert.equal(stopped.previewOpen, false)
  await controller.run('stop')
  assert.deepEqual(calls, ['open:index.html', 'show:index.html', 'close'])
  assert.ok(fs.existsSync(path.join(workspace, 'site/index.html')))
})

test('the control channel accepts only bounded preview actions', async context => {
  const { controller, calls } = fixture(context)
  assert.throws(() => dispatch(controller, { action: 'shell' }), /start, stop or status/)
  assert.throws(() => dispatch(controller, { action: 'start', command: 'x' }), /Unexpected/)
  assert.equal(dispatch(controller, { action: 'status' }).previewOpen, false)
  assert.deepEqual(calls, [])
})

test('rendering adds a no-network policy and a base for local assets', context => {
  const { workspace } = fixture(context)
  const target = resolveEntry(workspace)
  const vscode = {
    workspace: { textDocuments: [] },
    Uri: { file: value => value },
  }
  const webview = { cspSource: 'vscode-webview:', asWebviewUri: value => `webview:${value}` }
  const html = renderHtml(vscode, webview, target)
  assert.match(html, /<head><meta http-equiv="Content-Security-Policy"/)
  assert.ok(html.includes(`<base href="webview:${path.join(fs.realpathSync(workspace), 'site')}/">`))
  assert.ok(html.includes("default-src 'none'"))
  const policy = html.match(/content="([^"]+)"/)[1]
  const connect = policy.split(';').find(part => part.trim().startsWith('connect-src')).trim().split(/\s+/).slice(1)
  assert.deepEqual(connect, ['vscode-webview:', 'https://api.open-meteo.com', 'https://geocoding-api.open-meteo.com', 'https://archive-api.open-meteo.com'])
  assert.deepEqual(policy.match(/https:\/\/[^\s;]+/g), ['https://api.open-meteo.com', 'https://geocoding-api.open-meteo.com', 'https://archive-api.open-meteo.com'])
  const unsaved = { uri: { fsPath: target.file }, getText: () => '<html><head></head><body>Unsaved edit</body></html>' }
  vscode.workspace.textDocuments.push(unsaved)
  assert.ok(renderHtml(vscode, webview, target).includes('Unsaved edit'))
})

test('a new script, picture or data file redraws the page even when the page text is unchanged', async context => {
  const { workspace } = fixture(context)
  const target = resolveEntry(workspace)
  const drawn = []
  const listeners = {}
  const listen = name => handler => { listeners[name] = handler; return { dispose() {} } }
  const panel = {
    webview: {
      cspSource: 'vscode-webview:',
      asWebviewUri: value => `webview:${value}`,
      set html(value) { drawn.push(value) },
      onDidReceiveMessage: () => ({ dispose() {} }),
    },
    onDidDispose: () => ({ dispose() {} }),
  }
  const vscode = {
    workspace: {
      textDocuments: [],
      createFileSystemWatcher: () => ({ onDidChange: listen('change'), onDidCreate: listen('create'), onDidDelete: listen('delete'), dispose() {} }),
      onDidChangeTextDocument: listen('text'),
      onDidSaveTextDocument: listen('save'),
    },
    window: { createWebviewPanel: () => panel },
    Uri: { file: value => value },
    RelativePattern: class {},
    ViewColumn: { Beside: -2 },
  }
  createPreview(vscode, { workspaceState: { update() {} } }, workspace, target)
  listeners.create({ fsPath: path.join(workspace, 'site/js/workshop-chat.js') })
  await new Promise(resolve => setTimeout(resolve, 250))
  assert.equal(drawn.length, 2)
  assert.notEqual(drawn[0], drawn[1], 'a webview reloads only when its HTML text changes')
  assert.equal(drawn[0].replace(/<!-- preview draw \d+ -->/, ''), drawn[1].replace(/<!-- preview draw \d+ -->/, ''))
})

test('the preview always opens in the second column and starting it again keeps it there', context => {
  const { workspace } = fixture(context)
  const target = resolveEntry(workspace)
  const created = []
  const revealed = []
  const panel = {
    webview: { cspSource: 'vscode-webview:', asWebviewUri: value => `webview:${value}`, set html(value) {}, onDidReceiveMessage: () => ({ dispose() {} }) },
    onDidDispose: () => ({ dispose() {} }),
    reveal: (...args) => revealed.push(args),
  }
  const quiet = () => ({ dispose() {} })
  const vscode = {
    workspace: {
      textDocuments: [],
      createFileSystemWatcher: () => ({ onDidChange: quiet, onDidCreate: quiet, onDidDelete: quiet, dispose() {} }),
      onDidChangeTextDocument: quiet,
      onDidSaveTextDocument: quiet,
    },
    window: { createWebviewPanel: (...args) => { created.push(args); return panel } },
    Uri: { file: value => value },
    RelativePattern: class {},
    ViewColumn: { Beside: -2, Two: 2 },
  }
  const preview = createPreview(vscode, { workspaceState: { update() {} } }, workspace, target)
  assert.deepEqual(created[0][2], { viewColumn: 2, preserveFocus: true }, 'Beside the active column can add a third one')
  preview.show(target)
  assert.deepEqual(revealed, [[undefined, true]], 'moving it would add a column and unpin the tab')
})

function ask(endpoint, payload) {
  return new Promise((resolve, reject) => {
    const connection = net.createConnection(endpoint)
    let buffer = ''
    connection.once('connect', () => connection.write(JSON.stringify(payload) + '\n'))
    connection.on('data', chunk => { buffer += chunk })
    connection.once('end', () => resolve(JSON.parse(buffer.split('\n')[0])))
    connection.once('error', reject)
  })
}

test('the editor window focused most recently answers the preview helper', unixOnly, async context => {
  const { workspace } = fixture(context)
  const quiet = { appendLine() {} }
  const window = name => ({ status: () => ({ window: name }), run: async () => ({ window: name }) })
  let focusA = 0
  let focusB = 0
  const a = listen(workspace, window('A'), quiet, () => focusA, 1)
  const b = listen(workspace, window('B'), quiet, () => focusB, 2)
  context.after(() => { a.close(); b.close() })
  const endpoint = path.join(workspace, '.workshop-preview', 'site.sock')
  const answeredBy = async () => (await ask(endpoint, { action: 'status' })).result.window

  await a.settle()
  assert.equal(await answeredBy(), 'A')
  assert.equal(fs.statSync(endpoint).mode & 0o777, 0o600)
  await b.settle()
  await a.settle()
  assert.equal(await answeredBy(), 'B', 'when nobody has focused either, the newer window wins, as after a reload')

  focusA = 100
  await a.settle()
  await b.settle()
  assert.equal(await answeredBy(), 'A', 'the window in use takes over, and the other does not take it back')

  a.close()
  await new Promise(resolve => setTimeout(resolve, 50))
  await b.settle()
  assert.equal(await answeredBy(), 'B', 'a closed window hands over to one that is still open')
  assert.deepEqual(fs.readdirSync(path.dirname(endpoint)), ['site.sock'], 'no private socket names are left behind')
})

test('the preview helper never replaces a file it did not create', unixOnly, async context => {
  const { workspace } = fixture(context)
  const endpoint = path.join(workspace, '.workshop-preview', 'site.sock')
  fs.mkdirSync(path.dirname(endpoint))
  fs.writeFileSync(endpoint, 'not a socket')
  const helper = listen(workspace, {}, { appendLine() {} }, () => 0)
  context.after(() => helper.close())
  await assert.rejects(helper.settle(), /occupied by another file/)
  assert.equal(fs.readFileSync(endpoint, 'utf8'), 'not a socket')
})

test('an idea page finds the shared kit even when its paths were not rewritten', context => {
  const { workspace } = fixture(context)
  const site = path.join(fs.realpathSync(workspace), 'site')
  const idea = path.join(site, 'ideas', 'team-lunch')
  for (const file of ['css/workshop.css', 'js/workshop.js', 'js/vendor/three.module.js', 'art/monday.svg', 'images/my-photo.jpg', 'data/items.json']) {
    fs.mkdirSync(path.dirname(path.join(site, file)), { recursive: true })
    fs.writeFileSync(path.join(site, file), 'kit')
  }
  fs.mkdirSync(path.join(idea, 'data'), { recursive: true })
  fs.writeFileSync(path.join(idea, 'data', 'items.json'), '{}')
  const page = '<link rel="stylesheet" href="css/workshop.css"><script src="./js/workshop.js"></script>'
    + '<img src="art/monday.svg"><img src="../../art/monday.svg"><a href="data/items.json">data</a>'
    + '<img src="images/my-photo.jpg"><a href="https://example.com/x">link</a>'
    + "<script type=\"module\">import * as THREE from './js/vendor/three.module.js'</script>"
  fs.writeFileSync(path.join(idea, 'index.html'), `<html><head></head><body>${page}</body></html>`)
  const fixed = pointSharedFiles(page, idea, site)
  assert.ok(fixed.includes('href="../../css/workshop.css"'))
  assert.ok(fixed.includes('src="../../js/workshop.js"'))
  assert.equal((fixed.match(/src="\.\.\/\.\.\/art\/monday\.svg"/g) || []).length, 2, 'already-correct paths stay as they are')
  assert.ok(fixed.includes("from '../../js/vendor/three.module.js'"))
  assert.ok(fixed.includes('href="data/items.json"'), 'the page keeps its own data, even when site/ has one too')
  assert.ok(fixed.includes('src="../../images/my-photo.jpg"'), "the learner's own pictures are found too")
  assert.ok(fixed.includes('href="https://example.com/x"'), 'web addresses are never changed')
  assert.equal(pointSharedFiles(page, site, site), page, 'the first page is never changed')
  const vscode = { workspace: { textDocuments: [] }, Uri: { file: value => value } }
  const webview = { cspSource: 'vscode-webview:', asWebviewUri: value => `webview:${value}` }
  const html = renderHtml(vscode, webview, resolveEntry(workspace, 'ideas/team-lunch/index.html'))
  assert.ok(html.includes('href="../../css/workshop.css"'), 'the preview applies it')
})
