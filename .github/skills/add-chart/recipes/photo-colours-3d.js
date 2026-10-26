/* Recipe: "Color cloud" (3D) for the Photo Studio: the colors of the chosen photo as a cloud of dots in a red-green-blue cube.
 * Markup, after the studio panel:  <section class="panel animate-in chart-panel"><h2>The colors in your photo</h2><div class="chart chart-stage" id="colour-cloud" style="height: 380px"></div></section>
 * Script: add <script src="js/vendor/echarts.min.js"></script>, <script src="js/vendor/echarts-gl.min.js"></script> and
 * <script src="js/workshop-charts.js"></script> after workshop.js; call drawColourCloud(source) at the end of renderStage().
 * Check: pick the misty lake and the cloud turns mostly blue and gray; pick the fruit bowl and orange and green appear. */
function drawColourCloud(picture) {
    if (!picture) return
    const image = new Image()
    image.onload = () => {
        const canvas = document.createElement('canvas')
        canvas.width = 64
        canvas.height = 64
        const context = canvas.getContext('2d')
        context.drawImage(image, 0, 0, 64, 64)
        const pixels = context.getImageData(0, 0, 64, 64).data
        const stage = Workshop.stage3D(200)
        const data = []
        for (let index = 0; index < pixels.length; index += 4 * 3) {
            const [red, green, blue] = [pixels[index], pixels[index + 1], pixels[index + 2]]
            data.push({ value: [red, green, blue], itemStyle: { color: `rgb(${red}, ${green}, ${blue})` } })
        }
        const axis = name => ({ ...stage.axis, type: 'value', name, min: 0, max: 255 })
        Workshop.chart('#colour-cloud', {
            tooltip: { formatter: item => `Red ${item.value[0]}, green ${item.value[1]}, blue ${item.value[2]}` },
            xAxis3D: axis('Red'), yAxis3D: axis('Green'), zAxis3D: axis('Blue'),
            grid3D: { ...stage.grid3D, boxWidth: 100, boxDepth: 100, boxHeight: 100 },
            series: [{ type: 'scatter3D', data, symbolSize: 6, itemStyle: { opacity: 0.9 } }],
        })
    }
    image.src = picture
}
