const riskClass = risk => `pill ${risk}`;
export default function StudentPanel({students, showScore=true}) {
 return <section className="card"><div className="section-title">Student status <span>{students.length} tracked</span></div>
  <div className="student-list">{students.length?students.map(s=><div className="student" key={s.id}><div className="avatar">{String(s.track_id).padStart(2,'0')}</div><div><b>Student {s.track_id}</b><small>{s.seat_id||'Seat pending'}</small></div>{showScore&&<strong>{Math.round(s.risk_score)}</strong>}<span className={riskClass(s.risk_level)}>{s.risk_level}</span></div>):<p className="empty">Tracked students will appear here.</p>}</div>
 </section>
}
