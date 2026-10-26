/* Recipe: "Idea bubbles" (flat) for the Ideas Wall: every idea floats as a bubble you can drag around.
 * Markup, after the wall:  <section class="panel animate-in chart-panel"><h2>Idea bubbles</h2><div class="chart" id="idea-bubbles" style="height: 360px"></div></section>
 * Script: call drawIdeaBubbles() as the last line of render().
 * Check: add an idea and a new bubble floats in; drag a bubble and the others make room. */
function drawIdeaBubbles() {
    const colors = Workshop.chartColors()
    const style = getComputedStyle(document.body)
    const notes = ['--note-1', '--note-2', '--note-3', '--note-4'].map(name => style.getPropertyValue(name).trim())
    Workshop.chart('#idea-bubbles', {
        tooltip: { formatter: item => echarts.format.encodeHTML(item.name) },
        series: [{
            type: 'graph', layout: 'force', roam: false, draggable: true,
            force: { repulsion: 220, gravity: 0.12, edgeLength: 60 },
            data: state.items.map((item, index) => ({
                name: item.text,
                symbolSize: Math.min(120, 64 + item.text.length * 1.4),
                itemStyle: { color: notes[index % notes.length], borderColor: colors.line, borderWidth: 1, shadowBlur: 12, shadowColor: 'rgba(20, 40, 35, 0.18)' },
                label: { show: true, color: colors.ink, fontWeight: 700, width: 90, overflow: 'break', formatter: '{b}' },
            })),
            emphasis: { scale: 1.08 },
        }],
    })
}
