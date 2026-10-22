import {mediaUrl} from '../services/api';

export default function StudentPanel({students,alerts}) {
 const flagged=students.filter(s=>['medium','high','critical'].includes(s.risk_level));
 return <section className="card"><div className="section-title">Alert sidebar <span>{flagged.length} flagged</span></div>
  <div className="student-list">{flagged.length?flagged.map(s=>{
   const alert=alerts.find(a=>a.student_id===s.id);
   return <article className="student-alert" key={s.id}><div className="student"><div className="avatar">{String(s.track_id).padStart(2,'0')}</div><div><b>Tracked ID {s.track_id}</b><small>{alert?new Date(alert.created_at).toLocaleString():new Date(s.last_seen).toLocaleString()}</small></div><strong>{Math.round(s.risk_score)}</strong><span className={`pill ${s.risk_level}`}>{s.risk_level}</span></div>{alert?.evidence?.[0]&&<a href={mediaUrl(alert.evidence[0].frame_url)} target="_blank" rel="noreferrer"><img className="sidebar-evidence" src={mediaUrl(alert.evidence[0].frame_url)} alt={`Evidence for tracked ID ${s.track_id}`}/><small>Evidence · {alert.video_timestamp.toFixed(1)}s · Tracked ID {s.track_id}</small></a>}</article>
  }):<p className="empty">No medium-or-higher students.</p>}</div>
 </section>
}
