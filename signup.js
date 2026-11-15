// Newsletter sign-up box for LaughsLive.com.
// Plain form, no Brevo scripts or trackers on the page. On submit the email and city go
// straight to Brevo's form endpoint; Brevo then emails a confirmation link (double opt-in).
// Brevo form: "LaughsLive site sign-up" -> list "LaughsLive Newsletter", attribute CITY.
(function(){
  var ACTION="https://a5b89676.sibforms.com/serve/MUIFAC_kpUWNCi5NndC_TQfjAlTY6c-UdT4Dh1VsFZ_huu0pkoC2IkKFm6HJI1Vj_zI1iTe4SNDQ7cI-4TquSdRCx3WMsMx0m9e46I4pArD5A1USlZMWEg1Moqyt41NbzKcnUH2JEpkouWv1OUXu9I5Zxkm3wrLpHEmqxs7qyGlWYyZZqYLW__Lg0PuH_OloiMFXDVL1Fpf5u2oaEA==";
  function ready(fn){if(document.readyState==="loading")addEventListener("DOMContentLoaded",fn);else fn()}
  ready(function(){
    var box=document.getElementById("llSignup");if(!box)return;
    var form=box.querySelector("form"),sel=box.querySelector("select"),msg=box.querySelector(".llmsg");
    // City list from the app's own city names, alphabetical; default to the city being viewed.
    var names=(typeof CITY_NAME!=="undefined")?CITY_NAME:{};
    Object.keys(names).sort(function(a,b){return names[a].localeCompare(names[b])}).forEach(function(c){
      var o=document.createElement("option");o.value=names[c];o.textContent=names[c];sel.appendChild(o);
    });
    function syncCity(){try{var c=(window.LL_CITY&&names[window.LL_CITY])?window.LL_CITY:(typeof state!=="undefined"?state.city:null);if(c&&names[c])sel.value=names[c]}catch(e){}}
    syncCity();var cs=document.getElementById("citySel");if(cs)cs.addEventListener("change",function(){setTimeout(syncCity,0)});
    // Returning from the confirmation link
    if(/[?&]subscribed=1/.test(location.search)){msg.textContent="You're subscribed. Watch your inbox for this week's shows!";msg.hidden=false}
    form.addEventListener("submit",function(e){
      e.preventDefault();
      var email=form.EMAIL.value.trim();
      if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)){msg.textContent="Please enter a valid email address.";msg.hidden=false;return}
      var btn=form.querySelector("button");btn.disabled=true;
      var fd=new FormData(form);
      fetch(ACTION+"?isAjax=1",{method:"POST",body:fd,mode:"no-cors"}).then(function(){
        form.reset();syncCity();
        msg.textContent="Almost done: check your inbox for a confirmation email from LaughsLive and click the link to start getting shows.";
      }).catch(function(){
        msg.textContent="Something went wrong. Please try again in a minute.";
      }).then(function(){msg.hidden=false;btn.disabled=false});
    });
  });
})();
