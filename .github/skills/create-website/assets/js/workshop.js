/* Workshop helper kit: saving, local data, add buttons, drag and drop, and notices. No dependencies. */
(function () {
    'use strict'

    // The kit lives in site/js/. Shared files (art/, fonts/) sit next to that folder, wherever the
    // page is, so a second website in site/ideas/<name>/ finds them too.
    const kitRoot = typeof document !== 'undefined' && document.currentScript && document.currentScript.src
        ? new URL('..', document.currentScript.src) : null

    /** The address of a shared kit file, such as asset('art/monday.svg'), from any page. */
    function asset(file) {
        return kitRoot ? new URL(file, kitRoot).href : file
    }

    // Safety net: a picture in a second website (site/ideas/<name>/) that fails to load is tried
    // once more from site/, where the first page and the kit keep their pictures.
    if (kitRoot && typeof window.addEventListener === 'function') window.addEventListener('error', event => {
        const image = event.target
        if (!(image instanceof HTMLImageElement) || image.dataset.kitRetry) return
        const retry = image.src.replace(/\/ideas\/[^/]+\/(?!data\/)/, '/')
        if (retry === image.src) return
        image.dataset.kitRetry = 'yes'
        image.src = retry
    }, true)

    /** Remember one value in this browser. load() returns the fallback when nothing valid is saved. */
    function store(key) {
        return {
            load(fallback) {
                try {
                    const text = localStorage.getItem(key)
                    return text === null ? fallback : JSON.parse(text)
                } catch {
                    return fallback
                }
            },
            save(value) {
                try {
                    localStorage.setItem(key, JSON.stringify(value))
                    return true
                } catch {
                    return false
                }
            },
            clear() {
                try { localStorage.removeItem(key) } catch { /* storage unavailable */ }
            },
        }
    }

    /** Read JSON from a local file (such as data/tasks.json) or an allowed API; throws on failure. */
    async function getJSON(url) {
        const response = await fetch(url, { cache: 'no-store' })
        if (!response.ok) throw new Error(`Request failed (${response.status})`)
        return response.json()
    }

    /** Like getJSON, but returns the fallback instead of failing. */
    async function loadJSON(url, fallback) {
        try {
            return await getJSON(url)
        } catch {
            return fallback
        }
    }

    /**
     * Follow the page's own column list while keeping the entries saved in this browser.
     *
     * Columns describe the page, so renaming or replacing them shows straight away instead of
     * staying hidden behind entries saved on an earlier visit. Entries are the learner's work,
     * so they are kept; one pointing at a column that has gone moves to the first column
     * rather than disappearing.
     */
    function useColumns(state, columns, field = 'column') {
        if (!state || typeof state !== 'object') return state
        if (!Array.isArray(columns) || columns.length === 0) return state
        const items = Array.isArray(state.items) ? state.items : []
        return {
            ...state,
            columns: [...columns],
            items: items.map(item =>
                columns.includes(item[field]) ? item : { ...item, [field]: columns[0] }),
        }
    }

    /** Build an element safely: text is always set with textContent, never as HTML. */
    function el(tag, props = {}, ...children) {
        const node = document.createElement(tag)
        for (const [name, value] of Object.entries(props)) {
            if (value === undefined || value === null || value === false) continue
            if (name === 'className') node.className = value
            else if (name === 'text') node.textContent = value
            else if (name === 'style') node.setAttribute('style', value)
            else if (name.startsWith('on')) node.addEventListener(name.slice(2).toLowerCase(), value)
            else node.setAttribute(name, value === true ? '' : value)
        }
        for (const child of children.flat()) {
            if (child === null || child === undefined || child === false) continue
            node.append(child instanceof Node ? child : document.createTextNode(String(child)))
        }
        return node
    }

    /** A round + button that turns into a text box; Enter adds, Escape cancels. */
    function addButton(label, onAdd) {
        const wrapper = el('div', { className: 'add' })
        const button = el('button', { type: 'button', className: 'add-button', 'aria-label': label, title: label }, '+')
        wrapper.append(button)
        button.addEventListener('click', () => {
            const input = el('input', { className: 'add-input', 'aria-label': label, maxlength: '80', placeholder: label })
            const form = el('form', { className: 'add-form' }, input)
            const close = () => form.replaceWith(button)
            form.addEventListener('submit', event => {
                event.preventDefault()
                const text = input.value.trim()
                if (!text) return flash(input, 'shake')
                onAdd(text)
            })
            input.addEventListener('keydown', event => { if (event.key === 'Escape') { close(); button.focus() } })
            input.addEventListener('blur', () => { if (!input.value.trim()) close() })
            button.replaceWith(form)
            input.focus()
        })
        return wrapper
    }

    /**
     * Let items with data-card-id move between areas with data-column.
     * onMove(cardId, columnName, beforeCardId) updates the page's data and redraws;
     * beforeCardId is the card dropped onto, or null for the end of the column.
     */
    function enableBoard(board, onMove) {
        let dragged = null
        const clear = () => board.querySelectorAll('.is-over').forEach(node => node.classList.remove('is-over'))
        board.addEventListener('dragstart', event => {
            const card = event.target.closest('[data-card-id]')
            if (!card) return
            dragged = card.dataset.cardId
            card.classList.add('is-dragging')
            event.dataTransfer.effectAllowed = 'move'
            event.dataTransfer.setData('text/plain', dragged)
        })
        board.addEventListener('dragend', event => {
            event.target.closest('[data-card-id]')?.classList.remove('is-dragging')
            clear()
            dragged = null
        })
        board.addEventListener('dragover', event => {
            const column = event.target.closest('[data-column]')
            if (!column || dragged === null) return
            event.preventDefault()
            if (!column.classList.contains('is-over')) { clear(); column.classList.add('is-over') }
        })
        board.addEventListener('drop', event => {
            const column = event.target.closest('[data-column]')
            if (!column || dragged === null) return
            event.preventDefault()
            clear()
            const target = event.target.closest('[data-card-id]')
            const before = target && target.dataset.cardId !== dragged ? target.dataset.cardId : null
            onMove(dragged, column.dataset.column, before)
        })
    }

    let toastTimer
    /** Show a short message that screen readers also announce. */
    function toast(message) {
        let node = document.getElementById('workshop-toast')
        if (!node) {
            node = el('div', { id: 'workshop-toast', className: 'toast', role: 'status', 'aria-live': 'polite' })
            document.body.append(node)
        }
        node.textContent = message
        node.hidden = false
        flash(node, 'toast')
        clearTimeout(toastTimer)
        toastTimer = setTimeout(() => { node.hidden = true }, 2200)
    }

    /** Replay a one-off animation class such as "pop" or "shake". */
    function flash(node, name = 'pop') {
        if (!node) return
        node.classList.remove(name)
        void node.offsetWidth
        node.classList.add(name)
    }

    const newId = () => (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`)

    let previewChannel
    /**
     * The Website preview's message channel for the chat bubble and the photo studio, or null
     * anywhere else (such as a published copy). VS Code allows asking for it only once per page.
     */
    function preview() {
        if (previewChannel === undefined) {
            try {
                previewChannel = typeof acquireVsCodeApi === 'function' ? acquireVsCodeApi() : null
            } catch {
                previewChannel = null
            }
        }
        return previewChannel
    }

    window.Workshop = Object.assign(window.Workshop || {}, { store, getJSON, loadJSON, useColumns, el, addButton, enableBoard, toast, flash, newId, preview, asset })
})()
