/* Recipe: "Month in 3D" (3D) for the Calendar: one column per day of the month, as tall as its number of notes.
 * Markup, after the calendar panel:  <section class="panel animate-in chart-panel"><h2>Your month in 3D</h2><div class="chart chart-stage" id="month-3d" style="height: 380px"></div></section>
 * Script: also add <script src="js/vendor/echarts-gl.min.js"></script> after echarts.min.js; call drawMonth3D() as the last line of render().
 * Check: add a note today and today's column grows. Drag the chart to turn it. */
function drawMonth3D() {
    const colors = Workshop.chartColors()
    const stage = Workshop.stage3D(230)
    const pad = number => String(number).padStart(2, '0')
    const first = new Date(cursor.getFullYear(), cursor.getMonth(), 1)
    const last = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0).getDate()
    const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    const weeks = Math.ceil((first.getDay() + last) / 7)
    const data = Array.from({ length: last }, (_, index) => {
        const day = index + 1
        const key = `${first.getFullYear()}-${pad(first.getMonth() + 1)}-${pad(day)}`
        const slot = first.getDay() + index
        return { value: [slot % 7, Math.floor(slot / 7), state.items.filter(item => item.date === key).length], day }
    })
    Workshop.chart('#month-3d', {
        tooltip: { formatter: item => `${first.toLocaleDateString(undefined, { month: 'long' })} ${item.data.day}: <b>${item.value[2]} notes</b>` },
        visualMap: { show: false, min: 0, max: Math.max(1, ...data.map(entry => entry.value[2])), inRange: { color: [colors.sky, colors.accent, colors.sun, colors.coral] } },
        xAxis3D: { ...stage.axis, type: 'category', data: weekdays, name: '' },
        yAxis3D: { ...stage.axis, type: 'category', data: Array.from({ length: weeks }, (_, week) => `Week ${week + 1}`), name: '' },
        zAxis3D: { ...stage.axis, type: 'value', name: 'Notes', minInterval: 1 },
        grid3D: { ...stage.grid3D, boxWidth: 140, boxDepth: 100, boxHeight: 50 },
        series: [{ type: 'bar3D', data, minHeight: 0.6, shading: 'lambert', bevelSize: 0.4, bevelSmoothness: 4 }],
    })
}
