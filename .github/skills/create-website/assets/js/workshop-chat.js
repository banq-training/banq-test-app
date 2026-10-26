/* Optional "Ask my page" chat bubble: Workshop.addChat() adds a small assistant to any page.
 * It knows what the page shows, the page's own code, and the owner's notes in knowledge.md next
 * to the page. In the workshop's Website preview it asks the workshop's AI model;
 * the preview signs in, so the page holds no key or secret. On a published website it asks the
 * website's own /api/ask, which signs in with the website's Azure identity, again with no key.
 * Text is always set with textContent, never as HTML. */
(function () {
    'use strict'

    // Share the kit's one preview channel; an older workshop.js without it gets its own.
    let preview = null
    try {
        preview = window.Workshop && window.Workshop.preview ? window.Workshop.preview()
            : typeof acquireVsCodeApi === 'function' ? acquireVsCodeApi() : null
    } catch {
        preview = null
    }
    const waiting = new Map()

    window.addEventListener('message', event => {
        const reply = event.data
        if (!reply || reply.type !== 'workshop.answer' || !waiting.has(reply.id)) return
        const done = waiting.get(reply.id)
        waiting.delete(reply.id)
        done(reply)
    })

    /** Ask the Website preview; resolve with { ok, answer } or { ok: false, error }. */
    function askPreview(question, page, title, code, knowledge) {
        return new Promise(resolve => {
            const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
            const timer = setTimeout(() => {
                waiting.delete(id)
                resolve({ ok: false, error: 'No answer this time. Please try again.' })
            }, 45000)
            waiting.set(id, reply => { clearTimeout(timer); resolve(reply) })
            preview.postMessage({ type: 'workshop.ask', id, question, page, title, code, knowledge })
        })
    }

    /** On a published website, ask the website itself; resolve with { ok, answer } or { ok: false, error }. */
    async function askWebsite(question, page, title, code, knowledge) {
        const controller = new AbortController()
        const timer = setTimeout(() => controller.abort(), 45000)
        try {
            const response = await fetch('/api/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question, page, title, code, knowledge }),
                signal: controller.signal,
            })
            const reply = await response.json()
            if (reply && typeof reply.ok === 'boolean') return reply
        } catch {
            /* opened as a file, or the website could not answer: the plain message below */
        } finally {
            clearTimeout(timer)
        }
        return { ok: false, error: 'I answer questions while you build in the workshop preview. On this copy of the page I am switched off.' }
    }

    const STYLE = `
.chat { position: fixed; right: 1.2rem; bottom: 1.2rem; z-index: 20; display: flex; flex-direction: column; align-items: flex-end; gap: 0.6rem; }
.chat-toggle { display: inline-flex; align-items: center; gap: 0.5rem; border: 0; border-radius: 99px; padding: 0.75rem 1.15rem; background: var(--accent-strong); color: #fff; font: inherit; font-weight: 700; box-shadow: var(--shadow-lift); cursor: pointer; }
.chat-icon { position: relative; width: 1.15rem; height: 0.85rem; border-radius: 0.35rem; background: currentColor; }
.chat-icon::after { content: ""; position: absolute; left: 0.2rem; bottom: -0.32rem; border: 0.2rem solid transparent; border-top-color: currentColor; border-left-color: currentColor; }
.chat-panel { display: flex; flex-direction: column; width: min(22rem, calc(100vw - 2.4rem)); max-height: min(30rem, 70vh); overflow: hidden; background: var(--paper); color: var(--ink); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow-lift); }
.chat-panel[hidden] { display: none; }
.chat-head { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; padding: 0.7rem 0.9rem; background: var(--accent-soft); }
.chat-close { border: 0; background: transparent; color: inherit; font-size: 1.4rem; line-height: 1; cursor: pointer; }
.chat-log { flex: 1; display: flex; flex-direction: column; gap: 0.5rem; overflow-y: auto; padding: 0.8rem; }
.chat-bubble { max-width: 85%; margin: 0; padding: 0.55rem 0.8rem; border-radius: 1rem; line-height: 1.4; white-space: pre-wrap; }
.chat-bot { align-self: flex-start; background: var(--canvas); }
.chat-me { align-self: flex-end; background: var(--accent-strong); color: #fff; }
.chat-thinking { color: var(--muted); font-style: italic; }
.chat-form { display: flex; gap: 0.4rem; padding: 0.6rem; border-top: 1px solid var(--line); }
.chat-input { flex: 1; min-width: 0; padding: 0.55rem 0.85rem; border: 1px solid var(--line); border-radius: 99px; font: inherit; }
.chat-send { border: 0; border-radius: 99px; padding: 0.55rem 1rem; background: var(--accent-strong); color: #fff; font: inherit; font-weight: 700; cursor: pointer; }
.chat-send:disabled { opacity: 0.6; cursor: wait; }
.chat :focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
`

    function make(tag, className, text) {
        const node = document.createElement(tag)
        if (className) node.className = className
        if (text) node.textContent = text
        return node
    }

    /** The numbers behind each chart on the page, in plain words: a chart is a picture, so the
     *  visible text alone never shows what it plots. Works for any chart the kit or a page draws. */
    function chartText() {
        const charts = window.echarts ? document.querySelectorAll('[_echarts_instance_]') : []
        const label = value => (value && typeof value === 'object' && !Array.isArray(value)
            ? (value.name !== undefined ? `${value.name}: ` : '') + label(value.value)
            : Array.isArray(value) ? value.map(label).join(' / ') : String(value))
        const lines = []
        for (const element of charts) {
            let option
            try { option = window.echarts.getInstanceByDom(element).getOption() } catch { continue }
            const titles = [].concat(option.title || []).map(title => title && title.text).filter(Boolean)
            const near = element.closest('section, article, figure, .panel, .card')
            const heading = near && near.querySelector('h1, h2, h3, h4, figcaption')
            const name = titles[0] || element.getAttribute('aria-label') || (heading ? heading.innerText.trim() : 'Chart')
            const axis = [].concat(option.xAxis || option.angleAxis || option.yAxis || [])
                .map(item => item && Array.isArray(item.data) ? item.data.map(label) : null).find(Boolean)
            // 3D charts place each value at category positions: turn [x, y, height] into words.
            const axis3D = key => [].concat(option[key] || [])
                .map(item => item && Array.isArray(item.data) ? item.data.map(label) : null).find(Boolean)
            const x3D = axis3D('xAxis3D')
            const y3D = axis3D('yAxis3D')
            const point = value => {
                const raw = value && typeof value === 'object' && !Array.isArray(value) ? value.value : value
                if (x3D && Array.isArray(raw) && raw.length >= 3) {
                    const where = [x3D[raw[0]] ?? raw[0], y3D ? (y3D[raw[1]] ?? raw[1]) : null].filter(part => part !== null)
                    return `${value.name ? `${value.name} ` : ''}${where.join(', ')}: ${label(raw[2])}`
                }
                return label(value)
            }
            const series = [].concat(option.series || []).filter(item => !item.silent).map(item => {
                const data = (item.data || []).slice(0, 40).map((value, index) =>
                    axis && axis[index] !== undefined && typeof value !== 'object' ? `${axis[index]}: ${value}` : point(value))
                return `${item.name || item.type}: ${data.join(', ')}`
            })
            lines.push(`Chart "${name}": ${series.join('; ')}`.slice(0, 900))
        }
        return lines
    }

    /** The page's own code, so the assistant can explain how the page works: its scripts and styles
     *  first (so they survive the length limit), then the markup. The chat bubble itself and what the
     *  Website preview adds are left out. Shared kit files are not included, only this page. */
    function pageCode() {
        const copy = document.documentElement.cloneNode(true)
        for (const node of copy.querySelectorAll('#workshop-chat, base, meta[http-equiv]')) node.remove()
        const scripts = [...copy.querySelectorAll('script')].map(script => {
            const source = script.getAttribute('src')
            script.remove()
            return source ? `<script src="${source}"></script>` : `<script${script.type ? ` type="${script.type}"` : ''}>${script.textContent}</script>`
        })
        const styles = [...copy.querySelectorAll('style')].filter(style => !style.textContent.includes('.chat-toggle'))
            .map(style => { style.remove(); return `<style>${style.textContent}</style>` })
        for (const style of copy.querySelectorAll('style')) style.remove()
        return `Scripts:\n${scripts.join('\n')}\n\nStyles:\n${styles.join('\n')}\n\nMarkup:\n${copy.outerHTML}`.slice(0, 60000)
    }

    /** Extra facts the page's owner wrote in knowledge.md, next to the page. Read again for every
     *  question, so an edit counts at once; no file, or only comments, means no extra facts. */
    async function pageKnowledge() {
        try {
            const response = await fetch('knowledge.md', { cache: 'no-store' })
            if (!response.ok) return ''
            return (await response.text()).replace(/<!--[\s\S]*?-->/g, '').trim().slice(0, 20000)
        } catch {
            return ''
        }
    }

    /** What the assistant reads: the numbers behind charts, the ticked state of checkboxes and the
     *  descriptions of pictures, which the visible text leaves out, first (so they survive the
     *  length limit), then the visible text except the chat itself. */
    function pageText(widget) {
        widget.style.display = 'none'
        const text = document.body.innerText
        widget.style.display = ''
        const extras = []
        try { extras.push(...chartText()) } catch { /* a chart the page drew some other way */ }
        // Values typed into boxes, tables and choices are not part of the visible text either.
        const fields = document.querySelectorAll('input:not([type=checkbox]):not([type=radio]):not([type=hidden]):not([type=password]):not([type=file]), select, textarea')
        for (const field of [...fields].slice(0, 120)) {
            if (widget.contains(field) || !String(field.value || '').trim()) continue
            const label = field.labels && field.labels[0] ? field.labels[0].innerText : ''
            const name = (field.getAttribute('aria-label') || label || field.placeholder || field.name || 'Field').trim()
            const value = field.tagName === 'SELECT' && field.selectedOptions[0] ? field.selectedOptions[0].text : field.value
            extras.push(`${name}: ${String(value).trim().slice(0, 120)}`)
        }
        for (const box of document.querySelectorAll('input[type=checkbox]')) {
            const label = box.labels && box.labels[0] ? box.labels[0].innerText : ''
            const name = (box.getAttribute('aria-label') || label).trim()
            if (name) extras.push(`${box.checked ? 'Ticked' : 'Not ticked'}: ${name}`)
        }
        for (const picture of document.querySelectorAll('img[alt]')) {
            if (picture.alt.trim()) extras.push(`Picture: ${picture.alt.trim()}`)
        }
        return extras.length ? `Charts, typed values, checkboxes and pictures:\n${extras.join('\n')}\n\nPage text:\n${text}` : text
    }

    /** Add the chat bubble once; options: title, greeting, placeholder. */
    function addChat(options = {}) {
        if (document.getElementById('workshop-chat')) return
        const title = options.title || 'Ask my page'
        const style = make('style')
        style.textContent = STYLE
        document.head.append(style)

        const root = make('div', 'chat')
        root.id = 'workshop-chat'
        const toggle = make('button', 'chat-toggle')
        toggle.type = 'button'
        toggle.setAttribute('aria-expanded', 'false')
        toggle.setAttribute('aria-controls', 'workshop-chat-panel')
        toggle.append(make('span', 'chat-icon'), make('span', '', options.button || 'Ask'))
        const panel = make('section', 'chat-panel')
        panel.id = 'workshop-chat-panel'
        panel.hidden = true
        panel.setAttribute('aria-label', title)
        const head = make('div', 'chat-head')
        const close = make('button', 'chat-close', '\u00d7')
        close.type = 'button'
        close.setAttribute('aria-label', 'Close the chat')
        head.append(make('strong', '', title), close)
        const log = make('div', 'chat-log')
        log.setAttribute('role', 'log')
        log.setAttribute('aria-live', 'polite')
        const form = make('form', 'chat-form')
        const input = make('input', 'chat-input')
        input.type = 'text'
        input.maxLength = 200
        input.placeholder = options.placeholder || 'Ask a question'
        input.setAttribute('aria-label', 'Your question')
        const send = make('button', 'chat-send', 'Send')
        send.type = 'submit'
        form.append(input, send)
        panel.append(head, log, form)
        root.append(panel, toggle)
        document.body.append(root)

        const say = (who, text) => {
            const bubble = make('p', `chat-bubble chat-${who}`, text)
            log.append(bubble)
            log.scrollTop = log.scrollHeight
            return bubble
        }
        const open = show => {
            panel.hidden = !show
            toggle.setAttribute('aria-expanded', String(show))
            if (show) input.focus()
            else toggle.focus()
        }
        say('bot', options.greeting || 'Hi! Ask me anything about this page.')
        toggle.addEventListener('click', () => open(panel.hidden))
        close.addEventListener('click', () => open(false))
        panel.addEventListener('keydown', event => { if (event.key === 'Escape') open(false) })
        form.addEventListener('submit', async event => {
            event.preventDefault()
            const question = input.value.trim()
            if (!question || send.disabled) return
            input.value = ''
            say('me', question)
            send.disabled = true
            const thinking = say('bot chat-thinking', 'Thinking...')
            const page = pageText(root)
            let code = ''
            try { code = pageCode() } catch { /* the answer can still use what the page shows */ }
            const knowledge = await pageKnowledge()
            const reply = preview
                ? await askPreview(question, page, document.title, code, knowledge)
                : await askWebsite(question, page, document.title, code, knowledge)
            thinking.remove()
            send.disabled = false
            say('bot', reply.ok ? reply.answer : reply.error)
            input.focus()
        })
    }

    window.Workshop = Object.assign(window.Workshop || {}, { addChat })
})()
