import {useState} from 'react';
import {Upload, Play} from 'lucide-react';
import {mediaUrl} from '../services/api';
export default function VideoMonitor({analysis, onUpload, busy}) {
  const [model,setModel]=useState('yolo');
  return <section className="card monitor">
    <div className="section-title"><span>Classroom monitor</span><div className="upload-controls"><label className="model-picker">Model<select value={model} onChange={e=>setModel(e.target.value)} disabled={busy}><option value="yolo">YOLO26 Large</option><option value="sav">SAV MobileNet</option></select></label><label className={`upload${busy?' disabled':''}`}><Upload size={16}/>{busy?'Processing…':'Upload video'}<input type="file" accept="video/*" disabled={busy} onChange={e=>{const file=e.target.files[0];if(file)onUpload(file,model);e.target.value=''}}/></label></div></div>
    <div className="screen">{analysis?.output_url?<video src={mediaUrl(analysis.output_url)} controls/>:<><Play size={44}/><p>Upload an examination video to begin analysis</p></>}</div>
    {analysis&&<div className="progress"><div style={{width:`${analysis.progress}%`}}/><span>{analysis.status} · {Math.round(analysis.progress)}% · {analysis.model==='sav'?'SAV MobileNet':'YOLO26 Large'}</span></div>}
  </section>
}
