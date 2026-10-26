const fs = require('node:fs')
const path = require('node:path')

function resolveEntry(workspace, entry = 'index.html') {
  if (typeof entry !== 'string' || !entry || path.isAbsolute(entry) || /[\\:%?#]/.test(entry)) {
    throw new Error('Use an HTML path relative to site/, not a URL or absolute path.')
  }
  const parts = entry.split('/')
  if (parts.some(part => !part || part.startsWith('.')) || path.extname(entry) !== '.html') {
    throw new Error('The preview entry must be an HTML file inside site/.')
  }
  const root = fs.realpathSync(workspace)
  let current = path.join(root, 'site')
  for (const part of ['', ...parts]) {
    current = part ? path.join(current, part) : current
    if (!fs.existsSync(current)) {
      throw new Error('No saved website exists at this path. Use /create-website first.')
    }
    if (fs.lstatSync(current).isSymbolicLink()) {
      throw new Error('Preview paths must not contain symlinks.')
    }
  }
  if (!fs.statSync(current).isFile()) throw new Error('The preview entry must be a file.')
  return { entry, file: current, directory: path.dirname(current) }
}

class PreviewController {
  constructor(workspace, operations) {
    this.workspace = workspace
    this.operations = operations
    this.preview = undefined
    this.queue = Promise.resolve()
  }

  run(action, entry) {
    const result = this.queue.then(() => action === 'start' ? this.start(entry) : this.stop())
    this.queue = result.catch(() => {})
    return result
  }

  async start(entry) {
    const target = resolveEntry(this.workspace, entry)
    const reused = Boolean(this.preview?.isOpen())
    if (reused) await this.preview.show(target)
    else this.preview = await this.operations.open(target)
    return { ...this.status(), reused, message: 'Preview opened beside Chat. Changes appear automatically.' }
  }

  async stop() {
    if (this.preview?.isOpen()) this.preview.close()
    this.preview = undefined
    return { ...this.status(), message: 'Preview closed. Website files are unchanged.' }
  }

  status() {
    const open = Boolean(this.preview?.isOpen())
    return { previewOpen: open, entry: open ? this.preview.entry() : null, server: 'none', renderingVerified: false }
  }
}

module.exports = { PreviewController, resolveEntry }
