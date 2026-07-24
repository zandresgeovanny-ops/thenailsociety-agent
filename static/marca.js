// static/marca.js — Efectos de marca de The Nail Society Spa (aurora + brillo magnético)
// Externalizado desde branding.py para permitir una CSP estricta (sin scripts inline).
;(function(){
  var a=document.createElement("div");a.className="aurora";a.innerHTML='<b class="a"></b><b class="b"></b>';document.body.appendChild(a);
  var MAG=".btn.primary, form.card button";var CARDS=".tarjeta,.stat,.opt,.card,.panel";
  document.addEventListener("pointermove",function(e){
    if(!e.target.closest)return;
    var c=e.target.closest(CARDS);
    if(c){var r=c.getBoundingClientRect();c.style.setProperty("--mx",(e.clientX-r.left)+"px");c.style.setProperty("--my",(e.clientY-r.top)+"px");}
    var m=e.target.closest(MAG);
    if(m){var b=m.getBoundingClientRect();m.style.transform="translate("+((e.clientX-(b.left+b.width/2))*0.15).toFixed(1)+"px,"+((e.clientY-(b.top+b.height/2))*0.26).toFixed(1)+"px)";}
  });
  document.addEventListener("pointerout",function(e){if(e.target.closest){var m=e.target.closest(MAG);if(m)m.style.transform="";}});
})();
