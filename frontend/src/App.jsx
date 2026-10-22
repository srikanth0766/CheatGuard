import {useEffect,useState} from 'react';
import {ShieldCheck} from 'lucide-react';
import {api} from './services/api';
import VideoMonitor from './components/VideoMonitor';
import StudentPanel from './components/StudentPanel';
import LiveMonitor from './components/LiveMonitor';

export default function App(){
 const [analysis,setAnalysis]=useState(null),[students,setStudents]=useState([]),[alerts,setAlerts]=useState([]),[error,setError]=useState(''),[page,setPage]=useState('video');
 async function refreshAlerts(){try{setAlerts(await api('/api/alerts'))}catch(e){setError(e.message)}}
 async function upload(file){try{setError('');setStudents([]);const body=new FormData();body.append('video',file);const created=await api('/api/videos',{method:'POST',body});setAnalysis({...created,model:'sav-yolo',progress:0});await api(`/api/analysis/start?analysis_id=${created.analysis_id}`,{method:'POST'});}catch(e){setError(e.message)}}
 async function stopAnalysis(){try{const stopped=await api(`/api/analysis/${analysis.analysis_id}/stop`,{method:'POST'});setAnalysis(a=>({...a,...stopped}))}catch(e){setError(e.message)}}
 useEffect(()=>{refreshAlerts();const timer=setInterval(refreshAlerts,2000);return()=>clearInterval(timer)},[]);
 useEffect(()=>{if(!analysis||['completed','failed','cancelled'].includes(analysis.status))return;const timer=setInterval(async()=>{try{const status=await api(`/api/analysis/${analysis.analysis_id}`);setAnalysis(a=>({...a,...status}));setStudents(await api(`/api/students?analysis_id=${analysis.analysis_id}`));}catch(e){setError(e.message)}},2000);return()=>clearInterval(timer)},[analysis?.analysis_id,analysis?.status]);
 function selectAnalysis(id){setAnalysis({analysis_id:id,status:'running',model:'sav-yolo',progress:0});setStudents([])}
 const busy=analysis&&!['completed','failed','cancelled'].includes(analysis.status);
 return <><header><div className="brand"><ShieldCheck/><div><b>CHEATGUARD</b><small>Examination intelligence</small></div></div><nav><button className={page==='video'?'active':''} onClick={()=>setPage('video')}>Video analysis</button><button className={page==='live'?'active':''} onClick={()=>setPage('live')}>Live camera</button></nav><span className="live"><i/> SAV YOLO online</span></header><main>{error&&<div className="error">{error}</div>}<div className="grid">{page==='video'?<VideoMonitor analysis={analysis} onUpload={upload} onStop={stopAnalysis} busy={busy}/>:<LiveMonitor onStart={selectAnalysis} onError={e=>setError(e.message)}/>}<StudentPanel students={students} alerts={alerts}/></div></main></>
}
