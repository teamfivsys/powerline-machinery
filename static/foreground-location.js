"use strict";
// Same-origin foreground-only feature. No analytics, maps or third-party location calls.
(() => {
 const panel=document.getElementById("location-panel"); if(!panel)return;
 const start=document.getElementById("location-start"),stop=document.getElementById("location-stop"),state=document.getElementById("location-state");
 const csrf=document.querySelector("input[name=csrfmiddlewaretoken]").value;
 let token=null,watch=null,timer=null,starting=false,generation=0,lastSent=0,busy=false;
 const say=text=>{state.textContent=text;};
 const payload=(values)=>{const d=new FormData();d.append("csrfmiddlewaretoken",csrf);for(const [k,v] of Object.entries(values))d.append(k,v);return d;};
 async function post(url,values){const r=await fetch(url,{method:"POST",body:payload(values),credentials:"same-origin",cache:"no-store",redirect:"error"});if(!r.ok)throw new Error("Sharing request failed or expired.");return r.json();}
 function halt(text,beacon=false){
   generation++;starting=false;if(watch!==null)navigator.geolocation.clearWatch(watch);watch=null;clearTimeout(timer);timer=null;
   const old=token;token=null;start.disabled=false;stop.disabled=true;say(text);
   if(old){if(beacon)navigator.sendBeacon(panel.dataset.stop,payload({token:old}));else post(panel.dataset.stop,{token:old}).catch(()=>say("Sharing stopped on this page. The server may retain the last position until its two-minute expiry."));}
 }
 function expiry(){clearTimeout(timer);timer=setTimeout(()=>halt("Sharing stopped because no recent position was confirmed. Start again if needed."),105000);}
 start.addEventListener("click",async()=>{
   if(starting||token)return;
   if(!window.isSecureContext||!navigator.geolocation){say("Location needs HTTPS (or localhost) and browser support. No sharing was started.");return;}
   starting=true;lastSent=0;busy=false;start.disabled=true;stop.disabled=false;const gen=++generation;
   say("Starting foreground sharing; allow location only if you want to share for this job.");
   try{
     const data=await post(panel.dataset.start,{consent:"foreground"});
     if(gen!==generation||document.hidden){post(panel.dataset.stop,{token:data.token}).catch(()=>{});return;}
     starting=false;token=data.token;expiry();say("Sharing is on; waiting for browser permission and a position.");
     watch=navigator.geolocation.watchPosition(async position=>{
       if(gen!==generation||!token||document.hidden||busy)return;
       const now=Date.now();if(now-lastSent<10000)return;lastSent=now;busy=true;
       try{
         await post(panel.dataset.ping,{token,latitude:position.coords.latitude,longitude:position.coords.longitude,accuracy_m:position.coords.accuracy,captured_at:new Date(position.timestamp).toISOString()});
         if(gen===generation&&token){expiry();say("Sharing is on. Last position confirmed at "+new Date().toLocaleTimeString()+" (accuracy about "+Math.round(position.coords.accuracy)+" m).");}
       }catch(_){if(gen===generation)halt("Sharing stopped because the position could not be saved. Check connection, then start again.");}finally{busy=false;}
     },error=>{if(gen===generation)halt(error.code===1?"Location permission denied. Sharing is off.":"Location unavailable or timed out. Sharing is off.");},{enableHighAccuracy:true,maximumAge:0,timeout:20000});
   }catch(_){if(gen===generation)halt("Sharing could not start. Check your connection or sign in again.");}
 });
 stop.addEventListener("click",()=>halt("Location sharing is off."));
 document.addEventListener("visibilitychange",()=>{if(document.hidden&&(token||starting))halt("Sharing stopped when this page was hidden.",true);});
 window.addEventListener("pagehide",()=>halt("Location sharing is off.",true));
})();
