import {Upload, Play, Square} from 'lucide-react';
import {mediaUrl} from '../services/api';
export default function VideoMonitor({analysis, onUpload, onStop, busy}) {
  return <section className="card monitor">
    <div className="section-title"><span>Recorded video · SAV YOLO</span><div className="upload-controls"><label className={`upload${busy?' disabled':''}`}><Upload size={16}/>{busy?'Processing…':'Upload video'}<input type="file" accept="video/*" disabled={busy} onChange={e=>{const file=e.target.files[0];if(file)onUpload(file);e.target.value=''}}/></label>{busy&&<button className="stop" onClick={onStop}><Square size={15}/> Stop</button>}</div></div>
    <div className="screen">{analysis?.output_url?<video src={mediaUrl(analysis.output_url)} controls/>:<><Play size={44}/><p>Upload an examination video to begin analysis</p></>}</div>
    {analysis&&<div className="progress"><div style={{width:`${analysis.progress}%`}}/><span>{analysis.status} · {Math.round(analysis.progress)}% · SAV YOLO</span></div>}
  </section>
}
