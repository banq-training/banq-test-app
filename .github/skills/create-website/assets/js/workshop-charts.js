/* Charts for workshop pages, drawn by Apache ECharts (js/vendor/echarts.min.js) and, for 3D, by
 * ECharts GL (js/vendor/echarts-gl.min.js). Workshop.chart(box, option) draws an ECharts option
 * in the page's own colors and font, follows the box's size, and calms all motion when the
 * learner asks for less. A 3D chart in a browser without 3D shows a short note instead.
 * The libraries are local files: nothing here loads from the internet. Every text label is
 * drawn on a canvas; in a function tooltip formatter, wrap typed text in
 * echarts.format.encodeHTML. */
(function () {
    'use strict'

    const calm = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const THREE_D_PARTS = ['grid3D', 'geo3D', 'globe', 'mapbox3D']

    /** The page's colors, read from the kit's CSS variables, plus warm and cool extras. */
    function chartColors() {
        const style = getComputedStyle(document.body)
        const read = (name, fallback) => style.getPropertyValue(name).trim() || fallback
        return {
            accent: read('--accent', '#0b7a68'), strong: read('--accent-strong', '#075e50'),
            soft: read('--accent-soft', '#e3f4ef'), second: read('--second', '#3a6fd8'),
            ink: read('--ink', '#1d262b'), muted: read('--muted', '#5a676e'),
            line: read('--line', '#dce5e1'), paper: read('--paper', '#ffffff'),
            sun: '#f6b21a', coral: '#e4572e', sky: '#4aa3df', plum: '#8e5bd6',
            // Cold to hot, for temperatures and other "low to high" colors.
            heat: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#fee090', '#fdae61', '#f46d43', '#d73027'],
        }
    }

    /** True when this browser can draw 3D graphics (WebGL). */
    function can3D() {
        try {
            const canvas = document.createElement('canvas')
            return Boolean(canvas.getContext('webgl2') || canvas.getContext('webgl'))
        } catch {
            return false
        }
    }

    function needs3D(option) {
        const series = [].concat(option.series || [])
        return series.some(item => /(3D|GL)$/.test(item.type || '')) || THREE_D_PARTS.some(part => part in option)
    }

    function note(element, text) {
        const message = document.createElement('p')
        message.className = 'chart-note'
        message.textContent = text
        element.replaceChildren(message)
    }

    /** Stop spinning, rippling and trailing effects when the learner prefers reduced motion. */
    function calmDown(option) {
        for (const part of THREE_D_PARTS) {
            const viewControl = option[part] && option[part].viewControl
            if (viewControl) viewControl.autoRotate = false
        }
        for (const item of [].concat(option.series || [])) {
            if (item.type === 'effectScatter') item.type = 'scatter'
            if (item.effect) item.effect.show = false
        }
        return option
    }

    /**
     * Draw or redraw `option` inside `box` (an element or a CSS selector). Returns the ECharts
     * chart, or null when it cannot be drawn here (a short note explains why). Pass
     * { fresh: true } to start a new chart, for example when switching between 3D and flat.
     */
    function chart(box, option, settings = {}) {
        const element = typeof box === 'string' ? document.querySelector(box) : box
        if (!element) return null
        if (settings.fresh && window.echarts) window.echarts.getInstanceByDom(element)?.dispose()
        if (!window.echarts) {
            note(element, 'The chart library is missing: copy js/vendor/echarts.min.js beside this page.')
            return null
        }
        const threeD = needs3D(option)
        if (threeD && !window['echarts-gl']) {
            note(element, 'This 3D chart also needs js/vendor/echarts-gl.min.js.')
            return null
        }
        if (threeD && !can3D()) {
            note(element, 'This browser cannot draw 3D, so the 3D chart is switched off here.')
            return null
        }
        const colors = chartColors()
        const font = getComputedStyle(document.body).fontFamily
        let instance = window.echarts.getInstanceByDom(element)
        if (!instance) {
            element.replaceChildren()
            const created = window.echarts.init(element, null, { renderer: 'canvas' })
            instance = created
            const observer = new ResizeObserver(() => {
                if (created.isDisposed()) observer.disconnect()
                else created.resize()
            })
            observer.observe(element)
            // The kit font may arrive after the first drawing; redraw once it has.
            if (document.fonts) document.fonts.ready.then(() => { if (!created.isDisposed()) created.resize() })
        }
        const tooltip = option.tooltip === false ? { show: false } : {
            backgroundColor: colors.paper, borderColor: colors.line, borderWidth: 1, padding: [8, 12],
            textStyle: { color: colors.ink, fontFamily: font },
            extraCssText: 'border-radius: 12px; box-shadow: 0 10px 28px -12px rgb(20 40 35 / 40%);',
            ...(option.tooltip || {}),
        }
        const finished = {
            color: [colors.accent, colors.second, colors.sun, colors.coral, colors.sky, colors.plum, colors.strong],
            textStyle: { fontFamily: font, color: colors.ink },
            animationDuration: 900,
            animationEasing: 'cubicOut',
            ...option,
            tooltip,
        }
        if (calm) finished.animation = false
        instance.setOption(calm ? calmDown(finished) : finished, true)
        return instance
    }

    /**
     * Ready-made 3D settings for a dark .chart-stage box: light axis labels, soft grid lines,
     * good lighting and a slow turn that never captures the page's scrolling. Spread `axis`
     * into xAxis3D/yAxis3D/zAxis3D and `grid3D` into the option's grid3D.
     */
    function stage3D(distance = 220) {
        const text = '#d7e7ee'
        const line = { lineStyle: { color: 'rgba(255, 255, 255, 0.14)' } }
        return {
            axis: { axisLabel: { color: text, textStyle: { color: text } }, nameTextStyle: { color: text }, axisLine: line, axisTick: { show: false }, splitLine: line },
            grid3D: {
                axisLine: line, splitLine: line, axisPointer: { lineStyle: { color: '#ffffff' } },
                light: { main: { intensity: 1.5, shadow: true, alpha: 50, beta: 35 }, ambient: { intensity: 0.6 } },
                viewControl: { alpha: 22, beta: 35, distance, autoRotate: !calm, autoRotateSpeed: 5, autoRotateAfterStill: 4, zoomSensitivity: 0, panSensitivity: 0 },
            },
        }
    }

    window.Workshop = Object.assign(window.Workshop || {}, { chart, chartColors, can3D, stage3D })
})()
