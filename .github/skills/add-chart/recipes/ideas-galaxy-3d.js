/* Recipe: "Idea galaxy" (3D) for the Ideas Wall: the ideas shine as big stars in a slowly turning spiral of small ones.
 * Markup, after the wall:  <section class="panel animate-in chart-panel"><h2>Idea galaxy</h2><div class="chart chart-stage" id="idea-galaxy" style="height: 380px"></div></section>
 * Script: also add <script src="js/vendor/echarts-gl.min.js"></script> after echarts.min.js; call drawIdeaGalaxy() as the last line of render().
 * Check: add an idea and a new named star appears; drag to turn the galaxy. */
function drawIdeaGalaxy() {
    const stage = Workshop.stage3D(170)
    const style = getComputedStyle(document.body)
    const notes = ['--note-1', '--note-2', '--note-3', '--note-4'].map(name => style.getPropertyValue(name).trim())
    const hidden = { show: false }
    const axis = (min, max) => ({ ...stage.axis, axisLabel: hidden, splitLine: hidden, axisLine: hidden, name: '', min, max })
    // A fixed spiral of small stars, so the galaxy looks the same every time.
    const dust = Array.from({ length: 220 }, (_, index) => {
        const angle = index * 0.42
        const radius = 6 + index * 0.32
        return [Math.cos(angle) * radius, Math.sin(angle) * radius, Math.sin(index * 1.7) * 6]
    })
    const ideas = state.items.map((item, index) => {
        const angle = index * 2.1 + 0.6
        const radius = 22 + index * 9
        return {
            name: item.text, value: [Math.cos(angle) * radius, Math.sin(angle) * radius, 6 + (index % 3) * 6],
            itemStyle: { color: notes[index % notes.length], opacity: 1 },
        }
    })
    Workshop.chart('#idea-galaxy', {
        tooltip: { formatter: item => item.seriesIndex === 1 ? echarts.format.encodeHTML(item.name) : '' },
        xAxis3D: axis(-90, 90), yAxis3D: axis(-90, 90), zAxis3D: axis(-40, 40),
        grid3D: {
            ...stage.grid3D, show: false, boxWidth: 120, boxDepth: 120, boxHeight: 50,
            viewControl: { ...stage.grid3D.viewControl, alpha: 35, autoRotateSpeed: 8 },
            postEffect: { enable: true, bloom: { enable: true, bloomIntensity: 0.35 } },
        },
        series: [
            { type: 'scatter3D', silent: true, data: dust, symbolSize: 3, itemStyle: { color: '#9fd8ea', opacity: 0.55 } },
            {
                type: 'scatter3D', data: ideas, symbolSize: 26,
                label: { show: true, formatter: item => item.name, position: 'right', distance: 8, textStyle: { color: '#ffffff', fontSize: 14, fontWeight: 700, backgroundColor: 'rgba(10, 27, 35, 0.75)', padding: [4, 8], borderRadius: 6 } },
            },
        ],
    })
}
