import {useEffect,useState} from 'react';
import {ShieldCheck} from 'lucide-react';
import {api} from './services/api';
import VideoMonitor from './components/VideoMonitor';
import StudentPanel from './components/StudentPanel';
import AlertPanel from './components/AlertPanel';

export default function App(){
 const [analysis,setAnalysis]=useState(null),[students,setStudents]=useState([]),[alerts,setAlerts]=useState([]),[error,setError]=useState('');
 async function refreshAlerts(){try{setAlerts(await api('/api/alerts'))}catch(e){setError(e.message)}}
 async function upload(file,model){try{setError('');setStudents([]);const body=new FormData();body.append('video',file);const created=await api('/api/videos',{method:'POST',body});setAnalysis({...created,model,progress:0});await api(`/api/analysis/start?analysis_id=${created.analysis_id}&model=${model}`,{method:'POST'});}catch(e){setError(e.message)}}
 useEffect(()=>{refreshAlerts();const timer=setInterval(refreshAlerts,2000);return()=>clearInterval(timer)},[]);
 useEffect(()=>{if(!analysis||['completed','failed'].includes(analysis.status))return;const timer=setInterval(async()=>{try{const status=await api(`/api/analysis/${analysis.analysis_id}`);setAnalysis(a=>({...a,...status}));setStudents(await api(`/api/students?analysis_id=${analysis.analysis_id}`));}catch(e){setError(e.message)}},2000);return()=>clearInterval(timer)},[analysis?.analysis_id,analysis?.status]);
 return <><header><div className="brand"><ShieldCheck/><div><b>CHEATGUARD</b><small>Examination intelligence</small></div></div><span className="live"><i/> System online</span></header><main>{error&&<div className="error">{error}</div>}<div className="grid"><VideoMonitor analysis={analysis} onUpload={upload} busy={analysis&&!['completed','failed'].includes(analysis.status)}/><StudentPanel students={students} showScore={analysis?.model!=='sav'}/></div><AlertPanel alerts={alerts}/></main></>
}
