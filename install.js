// Small "add to home screen" tip for phones. iPhone Safari has no install prompt,
// so it shows instructions; Android/Chrome gets a real "Install" button.
(function(){
  var KEY="ll-install-dismissed";
  function dismissed(){try{return localStorage.getItem(KEY)==="1"}catch(e){return false}}
  function remember(){try{localStorage.setItem(KEY,"1")}catch(e){}}
  var standalone=matchMedia("(display-mode: standalone)").matches||navigator.standalone===true;
  if(standalone||dismissed())return;
  var ua=navigator.userAgent, ios=/iPhone|iPad|iPod/.test(ua)&&!/CriOS|FxiOS|EdgiOS/.test(ua), deferred=null;
  function show(html,onAction){
    if(document.getElementById("llInstall"))return;
    var bar=document.createElement("div");bar.id="llInstall";bar.setAttribute("role","note");
    bar.innerHTML='<style>#llInstall{position:fixed;left:12px;right:12px;bottom:calc(12px + env(safe-area-inset-bottom,0px));z-index:50;display:flex;gap:10px;align-items:center;'+
      'padding:12px 14px;border-radius:14px;background:var(--surface,#121834);color:var(--ink,#EEF0FF);border:1.5px solid var(--accent,#FF3EA5);'+
      'box-shadow:0 6px 24px rgba(0,0,0,.45);font:14px/1.4 system-ui,sans-serif;max-width:560px;margin:0 auto}'+
      '#llInstall img{width:36px;height:36px;border-radius:8px;flex:none}#llInstall p{margin:0;flex:1}'+
      '#llInstall button{font:inherit;font-weight:700;border-radius:10px;padding:8px 12px;border:0;cursor:pointer}'+
      '#llInstall .go{background:var(--accent,#FF3EA5);color:#fff}#llInstall .x{background:transparent;color:var(--muted,#9AA3C9);padding:8px}</style>'+
      '<img src="/icons/icon-192.png" alt=""><p>'+html+'</p>'+(onAction?'<button class="go" type="button">Install</button>':'')+
      '<button class="x" type="button" aria-label="Dismiss">✕</button>';
    document.body.appendChild(bar);
    bar.querySelector(".x").onclick=function(){remember();bar.remove()};
    if(onAction)bar.querySelector(".go").onclick=function(){onAction();bar.remove()};
  }
  addEventListener("beforeinstallprompt",function(e){e.preventDefault();deferred=e;
    setTimeout(function(){show("<b>Get the LaughsLive app</b> — one tap from your home screen.",function(){deferred.prompt();deferred.userChoice.then(remember)})},4000)});
  if(ios&&innerWidth<820)setTimeout(function(){show('<b>Add LaughsLive to your Home Screen:</b> tap <span aria-label="Share">Share <svg width="13" height="15" viewBox="0 0 13 15" style="vertical-align:-2px"><path d="M6.5 1v9M3 4l3.5-3L10 4M1.5 7v6.5h10V7" fill="none" stroke="currentColor" stroke-width="1.6"/></svg></span>, then “Add to Home Screen”.',null)},4000);
})();
