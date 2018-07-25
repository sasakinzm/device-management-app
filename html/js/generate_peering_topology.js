(function($){
  var urlParam = location.search.substring(1);
  if(urlParam) {
    var param = urlParam.split('&');
    var paramArray = [];
    for (i = 0; i < param.length; i++) {
      var paramItem = param[i].split('=');
      paramArray[paramItem[0]] = paramItem[1];
    }
  }

  var Renderer = function(canvas){
    var canvas = $(canvas).get(0)
    var ctx = canvas.getContext("2d");
    var gfx = arbor.Graphics(canvas);
    var particleSystem

    var that = {
      init:function(system){
        particleSystem = system
        particleSystem.screenSize(canvas.width, canvas.height)
        particleSystem.screenPadding(80)
        that.initMouseHandling()
      },
      redraw:function(){
        ctx.fillStyle = "white"
        ctx.fillRect(0,0, canvas.width, canvas.height)

        particleSystem.eachEdge(function(edge, pt1, pt2){
          ctx.strokeStyle = "rgba(0,0,0, .333)"
          ctx.lineWidth = 1
          ctx.beginPath()
          ctx.moveTo(pt1.x, pt1.y)
          ctx.lineTo(pt2.x, pt2.y)
          ctx.stroke()
        })

        // draw node box
        var nodeBoxes = {}
        particleSystem.eachNode(function(node, pt){
          var label = node.name||""
          var w = ctx.measureText(""+label).width + 10
          if (!(""+label).match(/^[ \t]*$/)){
            pt.x = Math.floor(pt.x)
            pt.y = Math.floor(pt.y)
          }else{
            label = null
          }
          
          if(node.data.who == "node")
          {
            ctx.fillStyle = "rgba(150,5,10,0.666)"
            gfx.oval(pt.x-w/2, pt.y-w/2, w,w, {fill:ctx.fillStyle})
          }
          else if(node.data.who == "peer")
          {
            ctx.fillStyle = "rgba(0,20,150,0.666)"
            gfx.rect(pt.x-w/2, pt.y-15, w,30, 4, {fill:ctx.fillStyle})
          }
          else
          {
            ctx.fillStyle = "rgba(0,0,0,0.666)"
            gfx.rect(pt.x-w/2, pt.y-10, w,20, 4, {fill:ctx.fillStyle})
          }
          nodeBoxes[node.name] = [pt.x-w/2, pt.y-11, w, 22]

          // draw the text
          if (label){
            ctx.font = "15px Helvetica"
            ctx.textAlign = "center"
            ctx.fillStyle = "white"
            if (node.data.color=='none') ctx.fillStyle = '#333333'
            ctx.fillText(label||"", pt.x, pt.y+4)
            ctx.fillText(label||"", pt.x, pt.y+4)
          }
        })
      },


      initMouseHandling:function(){
        var dragged = null;
        var handler = {
          clicked:function(e){
            var pos = $(canvas).offset();
            _mouseP = arbor.Point(e.pageX-pos.left, e.pageY-pos.top)
            dragged = particleSystem.nearest(_mouseP);

            if (dragged && dragged.node !== null){
              dragged.node.fixed = true
            }

            $(canvas).bind('mousemove', handler.dragged)
            $(window).bind('mouseup', handler.dropped)

            return false
          },
          dragged:function(e){
            var pos = $(canvas).offset();
            var s = arbor.Point(e.pageX-pos.left, e.pageY-pos.top)

            if (dragged && dragged.node !== null){
              var p = particleSystem.fromScreen(s)
              dragged.node.p = p
            }

            return false
          },

          dropped:function(e){
            if (dragged===null || dragged.node===undefined) return
            if (dragged.node !== null) dragged.node.fixed = false
            dragged.node.tempMass = 1000
            dragged = null
            $(canvas).unbind('mousemove', handler.dragged)
            $(window).unbind('mouseup', handler.dropped)
            _mouseP = null
            return false
          }
        }
        $(canvas).mousedown(handler.clicked);

      },

    }
    return that
  }

  $(document).ready(function(){
    var sys = arbor.ParticleSystem(1000, 60, 0.5)
    sys.parameters({gravity:true})
    sys.renderer = Renderer("#viewport")
    for (node in peerinfo) {
      for (let peer in peerinfo[node]) {
        if (peerinfo[node][peer].match(/ote/)) {
          sys.addNode(peerinfo[node][peer], {who:"node"});
        }
        else {
          sys.addNode(peerinfo[node][peer],{who:"peer"});
        }
        sys.addNode(node,{who:"node"});
        sys.addEdge(node, peerinfo[node][peer])
      }
    }
  })

})(this.jQuery)