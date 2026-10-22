import {useEffect,useRef,useState} from 'react';
import {Camera,Square} from 'lucide-react';
import {api,wsUrl} from '../services/api';

export default function LiveMonitor({onStart,onError}){
 const video=useRef(),canvas=useRef(),socket=useRef(),timer=useRef(),stream=useRef();
 const [running,setRunning]=useState(false),[frame,setFrame]=useState(''),[fps,setFps]=useState(0);
 const stop=()=>{clearInterval(timer.current);socket.current?.close();stream.current?.getTracks().forEach(t=>t.stop());setFrame(old=>{if(old)URL.revokeObjectURL(old);return ''});setRunning(false)};
 useEffect(()=>stop,[]);
 async function start(){try{
   stream.current=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:960},height:{ideal:540},frameRate:{ideal:24,min:24}},audio:false});
   video.current.srcObject=stream.current;await video.current.play();
   const session=await api('/api/live/start',{method:'POST'});onStart(session.analysis_id);
   const ws=new WebSocket(wsUrl(`/api/live/stream/${session.analysis_id}`));socket.current=ws;ws.binaryType='blob';
   let received=0,windowStart=performance.now(),waiting=false;
   ws.onmessage=e=>{waiting=false;received++;const now=performance.now();if(now-windowStart>=1000){setFps(Math.round(received*1000/(now-windowStart)));received=0;windowStart=now}setFrame(old=>{if(old)URL.revokeObjectURL(old);return URL.createObjectURL(e.data)})};
   ws.onerror=()=>onError(new Error('Live analysis connection failed'));
   ws.onopen=()=>{timer.current=setInterval(()=>{if(waiting||ws.readyState!==WebSocket.OPEN)return;const c=canvas.current;c.width=640;c.height=Math.round(640*video.current.videoHeight/video.current.videoWidth)||360;c.getContext('2d').drawImage(video.current,0,0,c.width,c.height);c.toBlob(blob=>{if(blob&&ws.readyState===WebSocket.OPEN){waiting=true;ws.send(blob)}},'image/jpeg',.72)},1000/24)};
   setRunning(true);
 }catch(e){stop();onError(e)}}
 return <section className="card monitor"><div className="section-title"><span>Live camera · SAV YOLO</span>{running?<button className="stop" onClick={stop}><Square size={15}/> Stop</button>:<button className="upload" onClick={start}><Camera size={16}/> Start camera</button>}</div><div className="live-stage"><video ref={video} className={frame?'source-video':''} muted playsInline/>{frame?<img src={frame}/>:<div className="camera-placeholder"><Camera size={44}/><p>Start the camera for live analysis</p><small>24 FPS camera target · latest-frame processing</small></div>}{running&&<span className="processing">Analyzed {fps} FPS · capture 24 FPS</span>}<canvas ref={canvas} hidden/></div></section>
}
