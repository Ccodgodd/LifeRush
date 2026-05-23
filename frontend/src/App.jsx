import React, { useState } from 'react';
import LandingPage from './pages/LandingPage.jsx';
import DonorDashboard from './pages/DonorDashboard.jsx';

export default function App() {
  const [authData, setAuthData] = useState(null);

  const handleLoginSuccess = (data) => {
    // data = { access_token, token_type, role, user_name, user_id }
    setAuthData(data);
  };

  const handleLogout = () => {
    setAuthData(null);
  };

  // Not logged in → show Landing / Auth page
  if (!authData) {
    return <LandingPage onLoginSuccess={handleLoginSuccess} />;
  }

  // Logged in → route by role
  const { access_token, role, user_name, user_id } = authData;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Top Navigation Bar */}
      <nav className="sticky top-0 z-50 glass-panel-heavy border-b border-slate-800/60">
        <div className="max-w-7xl mx-auto px-6 py-3 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-red-600 rounded-xl flex items-center justify-center shadow-lg shadow-red-500/20">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
              </svg>
            </div>
            <span className="text-lg font-bold bg-gradient-to-r from-white to-red-400 bg-clip-text text-transparent">
              LifeRush AI
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-400">
              Welcome, <span className="text-white font-semibold">{user_name}</span>
              <span className="ml-2 px-2 py-0.5 text-[10px] font-bold uppercase rounded bg-red-950 text-red-400 border border-red-900/20">
                {role}
              </span>
            </span>
            <button
              onClick={handleLogout}
              className="px-4 py-1.5 text-xs font-medium border border-slate-800 hover:border-red-500/40 hover:bg-red-950/20 text-slate-400 hover:text-red-400 rounded-lg transition-all"
            >
              Sign Out
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {role === 'donor' && (
          <DonorDashboard token={access_token} userName={user_name} userId={user_id} />
        )}
        {role === 'patient' && (
          <PatientDashboard token={access_token} userName={user_name} userId={user_id} />
        )}
        {role === 'admin' && (
          <AdminDashboard token={access_token} userName={user_name} userId={user_id} />
        )}
      </main>
    </div>
  );
}

// ============================================
// PATIENT DASHBOARD (Inline)
// ============================================
function PatientDashboard({ token, userName, userId }) {
  const [requests, setRequests] = useState([]);
  const [matches, setMatches] = useState([]);
  const [selectedRequestId, setSelectedRequestId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [hospitalQuery, setHospitalQuery] = useState('');
  const [hospitalResults, setHospitalResults] = useState([]);
  const [hospitalSearchLoading, setHospitalSearchLoading] = useState(false);
  const [hospitalSearchError, setHospitalSearchError] = useState('');
  const [userLocation, setUserLocation] = useState(null);
  const [formData, setFormData] = useState({
    blood_group: 'O+',
    units_needed: 1,
    hospital_name: '',
    hospital_location: '',
    hospital_address: '',
    hospital_place_id: '',
    latitude: null,
    longitude: null,
    urgency_level: 'medium',
    contact_number: ''
  });

  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };

  const fetchRequests = async () => {
    try {
      const res = await fetch('/api/v1/patients/requests', { headers });
      const data = await res.json();
      setRequests(data);
    } catch (err) {
      console.error(err);
    }
  };

  React.useEffect(() => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setUserLocation({
          lat: position.coords.latitude,
          lon: position.coords.longitude,
        });
      },
      () => setUserLocation(null),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 }
    );
  }, []);

  React.useEffect(() => {
    if (!showForm) return;

    const query = hospitalQuery.trim();
    if (query.length < 2) {
      setHospitalResults([]);
      setHospitalSearchError('');
      return;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(async () => {
      setHospitalSearchLoading(true);
      setHospitalSearchError('');

      try {
        const params = new URLSearchParams({ q: query });
        if (userLocation?.lat && userLocation?.lon) {
          params.set('lat', String(userLocation.lat));
          params.set('lon', String(userLocation.lon));
        } else if (formData.hospital_location) {
          params.set('city', formData.hospital_location);
        }

        const res = await fetch(`/api/v1/maps/hospitals/search?${params.toString()}`, {
          signal: controller.signal,
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Hospital search failed');
        setHospitalResults(data);
      } catch (err) {
        if (err.name !== 'AbortError') {
          setHospitalSearchError(err.message);
          setHospitalResults([]);
        }
      } finally {
        setHospitalSearchLoading(false);
      }
    }, 250);

    return () => {
      controller.abort();
      clearTimeout(timeoutId);
    };
  }, [hospitalQuery, showForm, userLocation, formData.hospital_location]);

  const fetchMatches = async (requestId) => {
    try {
      const res = await fetch(`/api/v1/patients/requests/${requestId}/matches`, { headers });
      const data = await res.json();
      setMatches(data);
      setSelectedRequestId(requestId);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateRequest = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch('/api/v1/patients/request', {
        method: 'POST',
        headers,
        body: JSON.stringify(formData)
      });
      if (res.ok) {
        setShowForm(false);
        setHospitalQuery('');
        setHospitalResults([]);
        fetchRequests();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSOS = async () => {
    setLoading(true);
    try {
      await fetch('/api/v1/patients/sos', { method: 'POST', headers });
      fetchRequests();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => { fetchRequests(); }, []);

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center border-b border-slate-900 pb-6">
        <div>
          <h2 className="text-3xl font-extrabold text-white">Patient / Hospital Dashboard</h2>
          <p className="text-slate-400 text-sm mt-1">Create blood requests, trigger SOS, and track matched donors.</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => setShowForm(!showForm)}
            className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white text-sm font-medium rounded-xl transition-all shadow-lg shadow-red-500/20">
            + New Request
          </button>
          <button onClick={handleSOS} disabled={loading}
            className="px-4 py-2 bg-red-800 hover:bg-red-700 text-white text-sm font-bold rounded-xl transition-all sos-pulse-effect">
            🆘 Emergency SOS
          </button>
        </div>
      </div>

      {showForm && (
        <form onSubmit={handleCreateRequest} className="glass-panel rounded-3xl p-6 border border-slate-800 grid grid-cols-2 gap-4">
          <div>
            <label className="block text-slate-300 text-xs font-semibold uppercase mb-1.5">Blood Group Needed</label>
            <select value={formData.blood_group} onChange={(e) => setFormData({...formData, blood_group: e.target.value})}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-red-500">
              {['O+','O-','A+','A-','B+','B-','AB+','AB-'].map(bg => <option key={bg} value={bg}>{bg}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-slate-300 text-xs font-semibold uppercase mb-1.5">Units Needed</label>
            <input type="number" min="1" value={formData.units_needed} onChange={(e) => setFormData({...formData, units_needed: parseInt(e.target.value)})}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-red-500" />
          </div>
          <div>
            <label className="block text-slate-300 text-xs font-semibold uppercase mb-1.5">Hospital Name</label>
            <div className="relative">
              <input type="text" required value={hospitalQuery} onChange={(e) => {
                const value = e.target.value;
                setHospitalQuery(value);
                setFormData({
                  ...formData,
                  hospital_name: value,
                  hospital_address: '',
                  hospital_place_id: '',
                  latitude: null,
                  longitude: null,
                });
              }}
                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-red-500" placeholder="Type hospital name" />
              {(hospitalSearchLoading || hospitalResults.length > 0 || hospitalSearchError) && (
                <div className="absolute z-20 mt-2 w-full overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 shadow-2xl">
                  {hospitalSearchLoading && <div className="px-3 py-2 text-xs text-slate-400">Searching hospitals...</div>}
                  {!hospitalSearchLoading && hospitalSearchError && <div className="px-3 py-2 text-xs text-red-400">{hospitalSearchError}</div>}
                  {!hospitalSearchLoading && !hospitalSearchError && hospitalResults.map((hospital) => (
                    <button
                      key={hospital.place_id}
                      type="button"
                      onClick={() => {
                        setHospitalQuery(hospital.name);
                        setHospitalResults([]);
                        setFormData({
                          ...formData,
                          hospital_name: hospital.name,
                          hospital_location: hospital.city || hospital.address,
                          hospital_address: hospital.address,
                          hospital_place_id: hospital.place_id,
                          latitude: hospital.latitude,
                          longitude: hospital.longitude,
                        });
                      }}
                      className="block w-full border-b border-slate-900 px-3 py-3 text-left transition-all hover:bg-slate-900 last:border-b-0"
                    >
                      <div className="text-sm font-semibold text-white">{hospital.name}</div>
                      <div className="text-xs text-slate-400">{hospital.address}</div>
                      <div className="mt-1 text-[10px] text-slate-500">
                        {hospital.distance_km ? `${hospital.distance_km} km away` : hospital.city || 'Hospital result'} • {hospital.source}
                      </div>
                    </button>
                  ))}
                  {!hospitalSearchLoading && !hospitalSearchError && hospitalResults.length === 0 && hospitalQuery.trim().length >= 2 && (
                    <div className="px-3 py-2 text-xs text-slate-500">No hospitals found.</div>
                  )}
                </div>
              )}
            </div>
          </div>
          <div>
            <label className="block text-slate-300 text-xs font-semibold uppercase mb-1.5">Hospital Location (City)</label>
            <input type="text" required value={formData.hospital_location} onChange={(e) => setFormData({...formData, hospital_location: e.target.value})}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-red-500" placeholder="San Francisco" />
          </div>
          <div className="col-span-2">
            <label className="block text-slate-300 text-xs font-semibold uppercase mb-1.5">Selected Address</label>
            <input type="text" value={formData.hospital_address} readOnly
              className="w-full bg-slate-950 border border-slate-900 rounded-xl px-3 py-2 text-slate-300 text-sm focus:outline-none"
              placeholder="Choose a hospital from suggestions to fill address" />
          </div>
          <div>
            <label className="block text-slate-300 text-xs font-semibold uppercase mb-1.5">Urgency Level</label>
            <select value={formData.urgency_level} onChange={(e) => setFormData({...formData, urgency_level: e.target.value})}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-red-500">
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="critical">Critical</option>
            </select>
          </div>
          <div>
            <label className="block text-slate-300 text-xs font-semibold uppercase mb-1.5">Contact Number</label>
            <input type="text" required value={formData.contact_number} onChange={(e) => setFormData({...formData, contact_number: e.target.value})}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-red-500" placeholder="Phone number" />
          </div>
          <div className="col-span-2 flex justify-end">
            <button type="submit" disabled={loading}
              className="px-6 py-2.5 bg-red-600 hover:bg-red-500 text-white text-sm font-medium rounded-xl transition-all">
              {loading ? 'Creating...' : 'Submit Blood Request'}
            </button>
          </div>
        </form>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Requests List */}
        <div className="lg:col-span-5 space-y-4">
          <h3 className="text-lg font-bold text-white">Your Blood Requests</h3>
          <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
            {requests.length === 0 ? (
              <div className="glass-panel rounded-2xl p-8 text-center text-slate-500 border border-slate-800">
                <p className="text-sm">No requests yet. Create one above.</p>
              </div>
            ) : requests.map((req) => (
              <div key={req.id} onClick={() => fetchMatches(req.id)}
                className={`glass-panel rounded-2xl p-4 border cursor-pointer transition-all ${
                  selectedRequestId === req.id ? 'border-red-500/40 bg-red-950/10' : 'border-slate-800 hover:border-slate-700'
                }`}>
                <div className="flex justify-between items-start">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded bg-red-950 text-red-400">{req.blood_group}</span>
                      <span className={`px-2 py-0.5 text-[10px] font-bold uppercase rounded ${
                        req.urgency_level === 'critical' ? 'bg-red-600 text-white animate-pulse' :
                        req.urgency_level === 'medium' ? 'bg-yellow-950 text-yellow-400' : 'bg-green-950 text-green-400'
                      }`}>{req.urgency_level}</span>
                    </div>
                    <h4 className="text-sm font-bold text-white mt-2">{req.hospital_name}</h4>
                    <p className="text-xs text-slate-400">{req.hospital_address || req.hospital_location} • {req.units_needed} unit(s)</p>
                  </div>
                  <span className="text-[10px] text-slate-500">{new Date(req.created_at).toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Matches Panel */}
        <div className="lg:col-span-7">
          <div className="glass-panel rounded-3xl p-6 border border-slate-800 min-h-[400px]">
            <h3 className="text-lg font-bold text-white mb-4">AI-Matched Donors</h3>
            {!selectedRequestId ? (
              <div className="flex flex-col items-center justify-center h-64 text-slate-500">
                <p className="text-sm">Select a request to view matched donors.</p>
              </div>
            ) : matches.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-64 text-slate-500">
                <p className="text-sm">No matches found for this request.</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
                {matches.map((match, idx) => (
                  <div key={match.id} className="p-4 bg-slate-900/60 rounded-2xl border border-slate-850 flex justify-between items-center">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-red-950/40 border border-red-800/20 rounded-full flex items-center justify-center text-red-400 font-bold text-sm">
                        #{idx + 1}
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-white">{match.donor_name}</h4>
                        <p className="text-xs text-slate-400">{match.donor_blood_group} • {match.donor_city} • {match.distance_km} km</p>
                        <p className="text-[10px] text-slate-500 mt-0.5">AI Score: {(match.score * 100).toFixed(1)}%</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`px-2 py-1 text-[10px] font-bold rounded uppercase ${
                        match.contact_status === 'accepted' ? 'bg-green-950 text-green-400' :
                        match.contact_status === 'declined' ? 'bg-red-950 text-red-400' :
                        'bg-yellow-950 text-yellow-400'
                      }`}>{match.contact_status}</span>
                      {match.eta && <p className="text-[10px] text-slate-400 mt-1">ETA: {match.eta}</p>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================
// ADMIN DASHBOARD (Inline)
// ============================================
function AdminDashboard({ token, userName, userId }) {
  const [stats, setStats] = useState(null);
  const headers = { 'Authorization': `Bearer ${token}` };

  React.useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch('/api/v1/admin/stats', { headers });
        const data = await res.json();
        setStats(data);
      } catch (err) {
        console.error(err);
      }
    };
    fetchStats();
  }, []);

  return (
    <div className="space-y-8">
      <div className="border-b border-slate-900 pb-6">
        <h2 className="text-3xl font-extrabold text-white">Admin Control Center</h2>
        <p className="text-slate-400 text-sm mt-1">System-wide analytics and metrics overview.</p>
      </div>

      {!stats ? (
        <div className="text-center text-slate-500 py-20">Loading admin analytics...</div>
      ) : (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="glass-panel rounded-2xl p-5 border border-slate-800">
              <div className="text-xs text-slate-400 font-semibold uppercase mb-1">Total Donors</div>
              <div className="text-3xl font-extrabold text-white">{stats.total_donors}</div>
            </div>
            <div className="glass-panel rounded-2xl p-5 border border-slate-800">
              <div className="text-xs text-slate-400 font-semibold uppercase mb-1">Total Patients</div>
              <div className="text-3xl font-extrabold text-white">{stats.total_patients}</div>
            </div>
            <div className="glass-panel rounded-2xl p-5 border border-slate-800">
              <div className="text-xs text-slate-400 font-semibold uppercase mb-1">Active Requests</div>
              <div className="text-3xl font-extrabold text-red-400">{stats.active_requests}</div>
            </div>
            <div className="glass-panel rounded-2xl p-5 border border-slate-800">
              <div className="text-xs text-slate-400 font-semibold uppercase mb-1">Successful Matches</div>
              <div className="text-3xl font-extrabold text-green-400">{stats.successful_matches}</div>
            </div>
          </div>

          {/* Detailed Tables */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="glass-panel rounded-3xl p-6 border border-slate-800">
              <h3 className="text-lg font-bold text-white mb-4">Requests by Blood Group</h3>
              <div className="space-y-3">
                {Object.entries(stats.requests_by_bg || {}).map(([bg, count]) => (
                  <div key={bg} className="flex justify-between items-center p-3 bg-slate-900/60 rounded-xl border border-slate-850">
                    <span className="text-sm font-bold text-white">{bg}</span>
                    <div className="flex items-center gap-3">
                      <div className="w-24 h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div className="h-full bg-red-500 rounded-full" style={{ width: `${Math.min(count * 20, 100)}%` }} />
                      </div>
                      <span className="text-sm font-bold text-slate-300 w-8 text-right">{count}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="glass-panel rounded-3xl p-6 border border-slate-800">
              <h3 className="text-lg font-bold text-white mb-4">Donors by City</h3>
              <div className="space-y-3">
                {Object.entries(stats.donors_by_city || {}).map(([city, count]) => (
                  <div key={city} className="flex justify-between items-center p-3 bg-slate-900/60 rounded-xl border border-slate-850">
                    <span className="text-sm font-bold text-white">{city}</span>
                    <div className="flex items-center gap-3">
                      <div className="w-24 h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div className="h-full bg-red-500 rounded-full" style={{ width: `${Math.min(count * 25, 100)}%` }} />
                      </div>
                      <span className="text-sm font-bold text-slate-300 w-8 text-right">{count}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
