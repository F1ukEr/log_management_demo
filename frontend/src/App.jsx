import { useState, useEffect } from 'react';
import axios from 'axios';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';

function App() {
  // State สำหรับระบบ Login
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [userRole, setUserRole] = useState('');
  const [userTenant, setUserTenant] = useState('');
  const [loginError, setLoginError] = useState('');

  // State สำหรับ Dashboard และ Data
  const [logs, setLogs] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [selectedTenant, setSelectedTenant] = useState('');

  // State สำหรับ Date Filter (ข้อ 2.2)
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  // State สำหรับช่องค้นหา (Search Box)
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (isLoggedIn) {
      fetchLogs(selectedTenant);
      fetchAlerts();
    }
  }, [isLoggedIn, selectedTenant]);

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post('http://127.0.0.1:8000/api/login', { username, password });
      setUserRole(response.data.role);
      setUserTenant(response.data.tenant);
      setIsLoggedIn(true);
      setLoginError('');
    } catch (error) {
      setLoginError('Login failed. Please check username and password.');
    }
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setUsername('');
    setPassword('');
    setLogs([]);
    setAlerts([]);
  };

  const fetchLogs = async (tenant) => {
    try {
      let url = 'http://127.0.0.1:8000/api/logs';
      if (tenant) url += `?tenant=${tenant}`;

      const response = await axios.get(url, {
        headers: { 'user-role': userRole, 'user-tenant': userTenant }
      });
      setLogs(response.data.data);
    } catch (error) {
      console.error("Error fetching logs:", error);
    }
  };

  const fetchAlerts = async () => {
    try {
      const response = await axios.get('http://127.0.0.1:8000/api/alerts');
      setAlerts(response.data.data);
    } catch (error) {
      console.error("Error fetching alerts:", error);
    }
  };
  // ฟังก์ชันสำหรับ File Upload และลบข้อมูลเก่า (Retention) - เฉพาะ Admin เท่านั้น
  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      await axios.post('http://127.0.0.1:8000/api/ingest/file_sample', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      alert("อัปโหลดไฟล์ Log สำเร็จ!");
      fetchLogs(selectedTenant); // โหลดตารางใหม่
    } catch (error) {
      alert("เกิดข้อผิดพลาดในการอัปโหลดไฟล์: ต้องเป็นไฟล์ JSON Array");
    }
  };

  const runRetention = async () => {
    try {
      const response = await axios.delete('http://127.0.0.1:8000/api/clear');
      alert(`ลบ Log ที่เก่ากว่า 7 วันสำเร็จแล้ว จำนวน: ${response.data.deleted_count} รายการ`);
      fetchLogs(selectedTenant);
    } catch (error) {
      alert("เกิดข้อผิดพลาดในการรัน Retention");
    }
  };

  // --- ระบบ Filter ข้อมูลตามช่วงเวลาที่เลือก (ข้อ 2.2) ---
  const filteredLogs = logs.filter(log => {
    let matchesSearch = true;
    if (startDate || endDate){
      const logDate = new Date(log.timestamp);
      const start = startDate ? new Date(startDate) : new Date('2000-01-01');
      const end = endDate ? new Date(endDate) : new Date('2100-01-01');
      end.setHours(23, 59, 59, 999); // ครอบคลุมถึงสิ้นสุดของวันนั้น
      matchesSearch = logDate >= start && logDate <= end;
    }
   let searchMatch = true;
    if (searchQuery) {
     const query = searchQuery.toLowerCase();
     const eventType = log.event_type ? log.event_type.toLowerCase() : "";
      const username = log.username ? log.username.toLowerCase() : "";
      const tenant = log.tenant ? log.tenant.toLowerCase() : "";
      const source = log.source ? log.source.toLowerCase() : "";
      searchMatch = eventType.includes(query) || username.includes(query) || tenant.includes(query) || source.includes(query);
      //searchMatch = log.event_type && log.event_type.toLowerCase().includes(query);
    }
    return matchesSearch && searchMatch;
    
  });

  // --- เตรียมข้อมูลสำหรับกราฟแท่ง (Top Event Types) ---
  const eventTypeStats = filteredLogs.reduce((acc, log) => {
    const type = log.event_type || 'unknown';
    const existing = acc.find(item => item.name === type);
    if (existing) existing.count += 1;
    else acc.push({ name: type, count: 1 });
    return acc;
  }, []);

  // --- เตรียมข้อมูลสำหรับกราฟเส้น Timeline (ข้อ 2.2) ---
  // จัดกลุ่มจำนวน Log ตามวัน/เวลา
  const timelineData = filteredLogs.reduce((acc, log) => {
    const dateStr = new Date(log.timestamp).toLocaleDateString();
    const existing = acc.find(item => item.date === dateStr);
    if (existing) {
      existing.count += 1;
    } else {
      acc.push({ date: dateStr, count: 1 });
    }
    return acc;
  }, []).reverse(); // กลับด้าน Array ให้อดีตอยู่ซ้าย ปัจจุบันอยู่ขวา

  
  // --- หน้าจอ Login ---
  if (!isLoggedIn) {
    return (
      <div style={{ maxWidth: '400px', margin: '100px auto', padding: '20px', border: '1px solid #ccc', borderRadius: '8px', fontFamily: 'sans-serif' }}>
        <h2>🔐 Log Management Login</h2>
        <form onSubmit={handleLogin}>
          <div style={{ marginBottom: '10px' }}>
            <label>Username: (admin หรือ viewer)</label>
            <input type="text" value={username} onChange={e => setUsername(e.target.value)} style={{ width: '100%', padding: '8px', marginTop: '5px' }} required />
          </div>
          <div style={{ marginBottom: '20px' }}>
            <label>Password: (ใส่ password123)</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} style={{ width: '100%', padding: '8px', marginTop: '5px' }} required />
          </div>
          {loginError && <p style={{ color: 'red' }}>{loginError}</p>}
          <button type="submit" style={{ width: '100%', padding: '10px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Login</button>
        </form>
      </div>
    );
  }
  
  // --- หน้าจอ Dashboard ---
  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>📊 Log Management Dashboard</h1>
        <div>
          <span style={{ marginRight: '15px' }}>👤 User: <strong>{username}</strong> (Role: {userRole})</span>
          <button onClick={handleLogout} style={{ padding: '8px 15px', backgroundColor: '#dc3545', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Logout</button>
        </div>
      </div>

      {/* แจ้งเตือน Alerts */}
      {alerts.length > 0 && (
        <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#ffebee', borderLeft: '5px solid #f44336', borderRadius: '4px' }}>
          <h3 style={{ color: '#d32f2f', marginTop: 0 }}>🚨 Active Alerts ({alerts.length})</h3>
          <ul style={{ margin: 0, paddingLeft: '20px' }}>
            {alerts.map(alert => (
              <li key={alert.id} style={{ marginBottom: '5px' }}>
                <strong>[{new Date(alert.timestamp).toLocaleTimeString()}]</strong> {alert.rule_name}: {alert.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Control Panel: Filters */}
      <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#f0f8ff', borderRadius: '8px', display: 'flex', gap: '20px', flexWrap: 'wrap' }}>

        {/* Filter by Tenant (โชว์เฉพาะ Admin) */}
        {userRole === 'admin' && (
          <div>
            <label style={{ fontWeight: 'bold', marginRight: '10px' }}>🏢 Tenant: </label>
            <select value={selectedTenant} onChange={(e) => setSelectedTenant(e.target.value)} style={{ padding: '5px' }}>
              <option value="">-- All Tenants --</option>
              <option value="demo">demo (API Logs)</option>
              <option value="demoA">demoA (Windows/CrowdStrike)</option>
              <option value="demoB">demoB (M365/AWS)</option>
            </select>
          </div>
        )}

        {/* Filter by Date Range */}
        <div>
          <label style={{ fontWeight: 'bold', marginRight: '10px' }}>📅 Date Range: </label>
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} style={{ padding: '5px' }} />
          <span style={{ margin: '0 10px' }}>ถึง</span>
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} style={{ padding: '5px' }} />
          <button onClick={() => { setStartDate(''); setEndDate(''); }} style={{ marginLeft: '10px', padding: '5px 10px', cursor: 'pointer' }}>Clear Date</button>
        </div>

      </div>
      {/* โซน File Batch Upload & Retention (เฉพาะ Admin) */}
      {userRole === 'admin' && (
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', borderLeft: '2px solid #ccc', paddingLeft: '20px' }}>
          <div>
            <label style={{ fontWeight: 'bold', display: 'block', fontSize: '12px' }}>📂 File Batch Upload (JSON)</label>
            <input type="file" accept=".json" onChange={handleFileUpload} style={{ fontSize: '12px' }} />
          </div>
          <div>
            <label style={{ fontWeight: 'bold', display: 'block', fontSize: '12px' }}>🧹 Data Retention</label>
            <button onClick={runRetention} style={{ padding: '5px 10px', backgroundColor: '#ff9800', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
              Run 7-Days Cleanup
            </button>
          </div>
          </div>
      )}
     

      {/* โซนแสดงกราฟ 2 ตัว (แท่ง และ เส้น) */}
      <div style={{ display: 'flex', gap: '20px', marginBottom: '40px', flexWrap: 'wrap' }}>

        {/* กราฟแท่ง (Top Event Types) */}
        <div style={{ height: '300px', flex: '1', minWidth: '400px', padding: '15px', border: '1px solid #eee', borderRadius: '8px' }}>
          <h3>📌 Top Event Types</h3>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={eventTypeStats}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#8884d8" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* กราฟเส้น (Timeline) - เพิ่มใหม่ตามโจทย์ข้อ 2.2 */}
        <div style={{ height: '300px', flex: '1', minWidth: '400px', padding: '15px', border: '1px solid #eee', borderRadius: '8px' }}>
          <h3>📈 Log Timeline (Events per Day)</h3>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={timelineData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="count" stroke="#82ca9d" strokeWidth={3} activeDot={{ r: 8 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

      </div>
      
        {/* โซนค้นหา Log ตาม Event Type */}
        <div>
          <label style={{ fontWeight: 'bold', marginRight: '10px' }}>🔍 Search: </label>
          <input 
            type="text" 
            placeholder="Search User, Event Type, Tenant, Source..." 
            value={searchQuery} 
            onChange={(e) => setSearchQuery(e.target.value)} 
            style={{ padding: '5px', width: '200px' }} 
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery('')} style={{ marginLeft: '5px', cursor: 'pointer', padding: '5px' }}>
              ❌
            </button>
          )}
        </div>
       
      {/* ตารางข้อมูล */}
      <h3>📋 Recent Logs ({filteredLogs.length} entries)</h3>
      <div style={{ overflowX: 'auto' }}>
        <table border="1" cellPadding="8" style={{ width: '100%', borderCollapse: 'collapse', minWidth: '800px' }}>
          <thead style={{ backgroundColor: '#f4f4f4', textAlign: 'left' }}>
            <tr>
              <th>Timestamp</th><th>Tenant</th><th>Source</th><th>Event Type</th><th>User</th><th>IP</th><th>Country (GeoIP)</th>
            </tr>
          </thead>
          <tbody>
            {filteredLogs.map((log) => {
              // ดึงข้อมูลประเทศที่จำลองไว้จาก JSONB (ถ้ามี)
              const country = log.raw && log.raw.enriched_country ? log.raw.enriched_country : '-';
              return (
                <tr key={log.id}>
                  <td>{new Date(log.timestamp).toLocaleString()}</td>
                  <td>{log.tenant}</td>
                  <td>{log.source}</td>
                  <td>{log.event_type}</td>
                  <td>{log.username || '-'}</td>
                  <td>{log.src_ip || '-'}</td>
                  <td>{country}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default App;