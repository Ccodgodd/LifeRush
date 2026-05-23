import React, { useState, useEffect, useRef } from 'react';
import { Heart, Activity, MapPin, MessageSquare, Bell, Calendar, ChevronRight, Send, User, Check, X, ShieldAlert, Award } from 'lucide-react';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { Bar } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

export default function DonorDashboard({ token, userName, userId }) {
  const [eligibility, setEligibility] = useState(null);
  const [history, setHistory] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [mapData, setMapData] = useState({ center: { lat: 37.77, lon: -122.41 }, places: [] });
  const [mapFilter, setMapFilter] = useState('hospital');
  const [mapLoading, setMapLoading] = useState(false);
  const [mapError, setMapError] = useState('');
  const [userLocation, setUserLocation] = useState(null);
  const [activeTab, setActiveTab] = useState('overview'); // overview, chatbot, map, history
  
  // Chat state
  const [chatMessages, setChatMessages] = useState([
    { role: 'assistant', text: 'Hello! I am your LifeRush AI Assistant. How can I help you regarding blood donations today?' }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Fetch all dashboard data
  const fetchDashboardData = async () => {
    try {
      const headers = { 'Authorization': `Bearer ${token}` };
      
      // Eligibility
      const eligRes = await fetch('/api/v1/donors/eligibility', { headers });
      const eligData = await eligRes.json();
      setEligibility(eligData);

      // Donation History
      const histRes = await fetch('/api/v1/donors/history', { headers });
      const histData = await histRes.json();
      setHistory(histData);

      // Notifications
      const notifRes = await fetch('/api/v1/donors/notifications', { headers });
      const notifData = await notifRes.json();
      setNotifications(notifData);
    } catch (err) {
      console.error('Error fetching donor data:', err);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    // Poll for notifications every 10 seconds
    const interval = setInterval(fetchDashboardData, 10000);
    return () => clearInterval(interval);
  }, []);

  // Fetch Nearby Map Data when eligibility is loaded or changed
  useEffect(() => {
    if (!navigator.geolocation) return;

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setUserLocation({
          lat: position.coords.latitude,
          lon: position.coords.longitude,
        });
      },
      () => {
        setUserLocation(null);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 }
    );
  }, []);

  useEffect(() => {
    const fetchMap = async () => {
      setMapLoading(true);
      setMapError('');

      try {
        const params = new URLSearchParams({
          radius_km: '12',
          place_type: mapFilter,
        });

        if (userLocation?.lat && userLocation?.lon) {
          params.set('lat', userLocation.lat.toString());
          params.set('lon', userLocation.lon.toString());
        } else {
          const city = userName?.includes('Hospital') ? 'Mumbai' : 'San Francisco';
          params.set('city', city);
        }

        const res = await fetch(`/api/v1/maps/nearby?${params.toString()}`);
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || 'Failed to load nearby facilities');
        }
        setMapData(data);
      } catch (err) {
        setMapError(err.message);
        console.error('Error loading nearby map:', err);
      } finally {
        setMapLoading(false);
      }
    };

    fetchMap();
  }, [mapFilter, userLocation, userName]);

  useEffect(() => {
    // Scroll chat to bottom
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const handleSendMessage = async (customMsg = '') => {
    const messageToSend = customMsg || chatInput;
    if (!messageToSend.trim()) return;

    setChatMessages(prev => [...prev, { role: 'user', text: messageToSend }]);
    if (!customMsg) setChatInput('');
    setChatLoading(true);

    try {
      const res = await fetch('/api/v1/chatbot/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: messageToSend })
      });
      const data = await res.json();
      setChatMessages(prev => [...prev, { role: 'assistant', text: data.reply }]);
    } catch (err) {
      setChatMessages(prev => [...prev, { role: 'assistant', text: 'Error connecting to chatbot server.' }]);
    } finally {
      setChatLoading(false);
    }
  };

  // Mark all notifications read
  const handleMarkRead = async () => {
    try {
      await fetch('/api/v1/donors/notifications/read', {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      fetchDashboardData();
    } catch (err) {
      console.error('Failed to mark read', err);
    }
  };

  // Accept a blood request matching notification
  const handleAcceptRequest = async (requestId, matchId) => {
    try {
      // Find matches for this request in backend and update the match status
      // We can search the database to update the match directly
      const response = await fetch(`/api/v1/patients/matches/${matchId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ contact_status: 'accepted', eta: '12 mins' })
      });
      if (response.ok) {
        alert('You have accepted this emergency donation request. Your ETA is set to 12 minutes.');
        fetchDashboardData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Decline a blood request matching notification
  const handleDeclineRequest = async (requestId, matchId) => {
    try {
      const response = await fetch(`/api/v1/patients/matches/${matchId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ contact_status: 'declined' })
      });
      if (response.ok) {
        alert('Request declined.');
        fetchDashboardData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Format Chart Data
  const getChartJsData = () => {
    if (!history || !history.chart_data) return { labels: [], datasets: [] };
    
    return {
      labels: history.chart_data.map(d => d.month),
      datasets: [
        {
          label: 'Blood Donations',
          data: history.chart_data.map(d => d.donations),
          backgroundColor: '#ef4444',
          borderRadius: 8,
        }
      ]
    };
  };

  const chartOptions = {
    responsive: true,
    scales: {
      y: {
        beginAtZero: true,
        ticks: { stepSize: 1, color: '#94a3b8' },
        grid: { color: '#1e293b' }
      },
      x: {
        ticks: { color: '#94a3b8' },
        grid: { display: false }
      }
    },
    plugins: {
      legend: { display: false },
    }
  };

  return (
    <div className="space-y-8 pb-16">
      
      {/* Upper Welcome Banner */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-900 pb-6">
        <div>
          <h2 className="text-3xl font-extrabold text-white">Donor Command Center</h2>
          <p className="text-slate-400 text-sm mt-1">Hello, {userName}. Track eligibility, explore map centers, and coordinate emergency SOS calls.</p>
        </div>
        
        {/* Navigation Tabs */}
        <div className="flex gap-2 bg-slate-900/60 p-1 rounded-xl border border-slate-800">
          {['overview', 'chatbot', 'map', 'history'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-1.5 text-xs font-semibold rounded-lg capitalize transition-all ${
                activeTab === tab ? 'bg-red-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Eligibility Card (Column Span 5) */}
          <div className="lg:col-span-5 space-y-6">
            <div className="glass-panel rounded-3xl p-6 border border-slate-800 relative overflow-hidden">
              <div className="absolute top-0 right-0 bg-red-600/10 text-red-500 font-bold px-4 py-2 rounded-bl-2xl border-l border-b border-red-500/10">
                Blood: {eligibility?.blood_group_extracted || 'O+'}
              </div>
              
              <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
                <Activity className="w-5 h-5 text-red-500" />
                Eligibility Profile
              </h3>

              {/* Status Badge */}
              <div className="flex items-center gap-4 mb-6">
                <div className={`p-3.5 rounded-2xl ${
                  eligibility?.is_eligible ? 'bg-green-950/20 text-green-500 border border-green-800/30' : 'bg-red-950/20 text-red-500 border border-red-800/30'
                }`}>
                  <Heart className={`w-8 h-8 ${eligibility?.is_eligible ? 'fill-green-500' : ''}`} />
                </div>
                <div>
                  <div className="text-xs text-slate-400 font-semibold uppercase">Current Status</div>
                  <div className={`text-xl font-extrabold ${eligibility?.is_eligible ? 'text-green-400' : 'text-red-400'}`}>
                    {eligibility?.is_eligible ? 'Eligible to Donate' : 'Not Eligible'}
                  </div>
                </div>
              </div>

              {/* Medical Details Table */}
              <div className="space-y-4 border-t border-slate-800/60 pt-4">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-slate-400">Hemoglobin (Hb)</span>
                  <span className="text-white font-bold">{eligibility?.hemoglobin || 0.0} g/dL</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-slate-400">Platelet Count</span>
                  <span className="text-white font-bold">{eligibility?.platelets ? eligibility.platelets.toLocaleString() : 0} /mcL</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-slate-400">WBC Count</span>
                  <span className="text-white font-bold">{eligibility?.wbc_count ? eligibility.wbc_count.toLocaleString() : 0} /uL</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-slate-400">Next Eligible Date</span>
                  <span className="text-white font-bold flex items-center gap-1">
                    <Calendar className="w-4 h-4 text-red-400" />
                    {eligibility?.next_eligible_date || 'Today'}
                  </span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-slate-400">Biological Risk Level</span>
                  <span className={`px-2 py-0.5 text-xs font-semibold rounded ${
                    eligibility?.risk_level === 'Low' ? 'bg-green-950 text-green-400' : 
                    eligibility?.risk_level === 'Medium' ? 'bg-yellow-950 text-yellow-400' : 'bg-red-950 text-red-400'
                  }`}>{eligibility?.risk_level || 'Low'}</span>
                </div>
              </div>

              {/* Ineligibility alerts */}
              {!eligibility?.is_eligible && eligibility?.ineligibility_reason && (
                <div className="mt-6 p-4 rounded-xl bg-red-950/20 border border-red-900/40 text-red-400 text-xs flex gap-2">
                  <ShieldAlert className="w-5 h-5 shrink-0" />
                  <span><strong>Reason:</strong> {eligibility.ineligibility_reason}</span>
                </div>
              )}
            </div>

            {/* Quick Stats Block */}
            <div className="grid grid-cols-2 gap-4">
              <div className="glass-panel rounded-2xl p-5 border border-slate-800">
                <div className="text-xs text-slate-400 font-semibold uppercase mb-1">Estimated Lives Saved</div>
                <div className="text-3xl font-extrabold text-white flex items-center gap-2">
                  <Award className="w-7 h-7 text-yellow-500" />
                  {history?.estimated_lives_saved || 0}
                </div>
              </div>
              <div className="glass-panel rounded-2xl p-5 border border-slate-800">
                <div className="text-xs text-slate-400 font-semibold uppercase mb-1">Total Donations</div>
                <div className="text-3xl font-extrabold text-white">{history?.total_donations || 0}</div>
              </div>
            </div>
          </div>

          {/* Right Area: Alerts Center & Activity Log (Column Span 7) */}
          <div className="lg:col-span-7 space-y-6">
            <div className="glass-panel rounded-3xl p-6 border border-slate-800 min-h-[400px] flex flex-col">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Bell className="w-5 h-5 text-red-500" />
                  Alerts & Matches Notification Inbox
                </h3>
                {notifications.some(n => !n.is_read) && (
                  <button onClick={handleMarkRead} className="text-xs text-red-400 hover:underline">
                    Mark all read
                  </button>
                )}
              </div>

              <div className="space-y-4 flex-1 overflow-y-auto max-h-[360px] pr-2">
                {notifications.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 py-12">
                    <Bell className="w-12 h-12 mb-3 text-slate-700" />
                    <p className="text-sm">No new requests or reminders.</p>
                  </div>
                ) : (
                  notifications.map((notif) => (
                    <div 
                      key={notif.id} 
                      className={`p-4 rounded-2xl border transition-all ${
                        notif.type === 'emergency' 
                          ? 'bg-red-950/20 border-red-500/20 hover:border-red-500/40' 
                          : 'bg-slate-900/40 border-slate-850 hover:border-slate-800'
                      } ${!notif.is_read ? 'ring-1 ring-red-500/30' : ''}`}
                    >
                      <div className="flex justify-between items-start gap-4">
                        <div>
                          <div className="flex items-center gap-2">
                            {notif.type === 'emergency' && (
                              <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded bg-red-600 text-white animate-pulse">SOS</span>
                            )}
                            <span className="text-sm font-bold text-white">{notif.title}</span>
                          </div>
                          <p className="text-xs text-slate-400 mt-1">{notif.message}</p>
                          <span className="text-[10px] text-slate-500 mt-2 block">
                            {new Date(notif.created_at).toLocaleString()}
                          </span>
                        </div>
                        
                        {/* If it's an emergency notification and has an active match decision context */}
                        {notif.type === 'emergency' && notif.message.includes('Can you donate?') && (
                          <div className="flex gap-2">
                            {/* We simulate resolving the match ID based on request or allow simulation */}
                            <button
                              onClick={() => {
                                // Since match ID is tied to database routing, we trigger simulated accept
                                // We can fetch the match details using a generic helper or scan notification text.
                                // Here, we trigger simulated response
                                handleAcceptRequest('req_id', notif.id);
                              }}
                              className="p-1.5 bg-green-600 text-white rounded-lg hover:bg-green-500 transition-all"
                              title="Accept Donation Match"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleDeclineRequest('req_id', notif.id)}
                              className="p-1.5 bg-slate-800 text-slate-400 rounded-lg hover:bg-red-600 hover:text-white transition-all"
                              title="Decline Match"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

        </div>
      )}

      {/* AI Chatbot Tab */}
      {activeTab === 'chatbot' && (
        <div className="max-w-4xl mx-auto glass-panel rounded-3xl p-6 border border-slate-800 h-[600px] flex flex-col">
          
          <div className="flex items-center gap-3 border-b border-slate-800 pb-4 mb-4">
            <div className="w-10 h-10 rounded-xl bg-red-600/10 border border-red-500/20 flex items-center justify-center text-red-500">
              <MessageSquare className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">AI Medical Guidance</h3>
              <p className="text-xs text-slate-400">Ask eligibility criteria, foods, intervals, or donor directions.</p>
            </div>
          </div>

          {/* Quick FAQ Tags */}
          <div className="flex flex-wrap gap-2 mb-4">
            {[
              "Am I eligible to donate?",
              "How often can I donate?",
              "What foods increase hemoglobin?",
              "Where can I donate nearby?"
            ].map((q) => (
              <button
                key={q}
                onClick={() => handleSendMessage(q)}
                className="px-3 py-1.5 bg-slate-900/60 border border-slate-800 hover:border-red-500/30 rounded-full text-xs text-slate-300 hover:text-white transition-all"
              >
                {q}
              </button>
            ))}
          </div>

          {/* Message Area */}
          <div className="flex-1 overflow-y-auto space-y-4 pr-2 mb-4 scrollbar-thin">
            {chatMessages.map((msg, idx) => (
              <div 
                key={idx} 
                className={`flex gap-3 max-w-[85%] ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs shrink-0 ${
                  msg.role === 'user' ? 'bg-red-600 text-white' : 'bg-slate-800 text-red-500'
                }`}>
                  {msg.role === 'user' ? <User className="w-4 h-4" /> : <Heart className="w-4 h-4" />}
                </div>
                <div className={`p-4 rounded-2xl text-sm leading-relaxed whitespace-pre-line ${
                  msg.role === 'user' 
                    ? 'bg-red-600 text-white rounded-tr-none' 
                    : 'bg-slate-900/80 border border-slate-850 text-slate-200 rounded-tl-none'
                }`}>
                  {msg.text}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="flex gap-3 max-w-[80%]">
                <div className="w-8 h-8 rounded-full bg-slate-800 text-red-500 flex items-center justify-center text-xs">
                  <Heart className="w-4 h-4" />
                </div>
                <div className="bg-slate-900/80 border border-slate-850 p-4 rounded-2xl rounded-tl-none text-sm text-slate-400 flex items-center gap-2">
                  <div className="flex gap-1">
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                  </div>
                  LifeRush AI is thinking...
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Form Input */}
          <div className="flex gap-2">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleSendMessage(); }}
              placeholder="Ask anything about blood donation..."
              className="flex-1 bg-slate-900 border border-slate-800 focus:border-red-500 rounded-xl px-4 py-3 text-white placeholder-slate-500 text-sm focus:outline-none"
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={chatLoading}
              className="px-4 bg-red-600 hover:bg-red-500 text-white rounded-xl flex items-center justify-center transition-all"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>

        </div>
      )}

      {/* Map Tab */}
      {activeTab === 'map' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Locations Side Panel */}
          <div className="lg:col-span-5 space-y-4">
            <div className="glass-panel rounded-3xl p-5 border border-slate-800">
              <h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
                <MapPin className="w-5 h-5 text-red-500" />
                Active Donation Centers
              </h3>
              <p className="text-xs text-slate-400 mb-4">
                Showing nearby facilities {userLocation ? 'around your current location' : 'based on fallback city matching'}.
              </p>
              <div className="flex gap-2 mb-4">
                {[
                  { id: 'hospital', label: 'Hospitals' },
                  { id: 'blood_bank', label: 'Blood Banks' },
                  { id: 'donation_camp', label: 'Donation Camps' },
                  { id: 'all', label: 'All' },
                ].map((filter) => (
                  <button
                    key={filter.id}
                    onClick={() => setMapFilter(filter.id)}
                    className={`px-3 py-1.5 rounded-full text-[11px] font-semibold transition-all ${
                      mapFilter === filter.id
                        ? 'bg-red-600 text-white'
                        : 'bg-slate-900/60 border border-slate-800 text-slate-300'
                    }`}
                  >
                    {filter.label}
                  </button>
                ))}
              </div>
              {mapLoading && <p className="text-xs text-slate-500 mb-3">Loading real nearby places...</p>}
              {mapError && <p className="text-xs text-red-400 mb-3">{mapError}</p>}
              
              <div className="space-y-3 max-h-[420px] overflow-y-auto pr-2">
                {mapData.places.map((place, idx) => (
                  <div key={idx} className="p-3 bg-slate-900/60 hover:bg-slate-900 border border-slate-850 hover:border-slate-800 rounded-2xl transition-all cursor-pointer">
                    <div className="flex justify-between items-start">
                      <span className="px-2 py-0.5 text-[9px] font-bold rounded bg-red-950 text-red-400 border border-red-900/20">{place.type}</span>
                      <span className="text-[10px] text-slate-500">{place.distance_km ? `${place.distance_km} km` : ''}</span>
                    </div>
                    <h4 className="text-sm font-bold text-white mt-1.5">{place.name}</h4>
                    <p className="text-xs text-slate-400 font-light mt-0.5">{place.address}</p>
                    <p className="text-[10px] text-slate-500 mt-1">Tel: {place.contact}</p>
                    <p className="text-[10px] text-slate-600 mt-1">Source: {place.source || mapData.source}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* SVG Map Grid Simulator (Column Span 7) */}
          <div className="lg:col-span-7">
            <div className="glass-panel rounded-3xl p-6 border border-slate-800 h-[530px] flex flex-col">
              <h3 className="text-sm font-bold text-slate-300 mb-4 flex items-center gap-2">
                Interactive Google Maps Simulation Panel
              </h3>
              
              {/* Map grid screen */}
              <div className="flex-1 bg-slate-950 rounded-2xl border border-slate-900 relative overflow-hidden flex items-center justify-center">
                {/* SVG coordinate overlay */}
                <svg className="absolute inset-0 w-full h-full text-slate-900" xmlns="http://www.w3.org/2000/svg">
                  <defs>
                    <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
                      <path d="M 30 0 L 0 0 0 30" fill="none" stroke="currentColor" strokeWidth="0.5" />
                    </pattern>
                  </defs>
                  <rect width="100%" height="100%" fill="url(#grid)" />
                  
                  {/* Concentric distance circles */}
                  <circle cx="50%" cy="50%" r="60" fill="none" stroke="#ef4444" strokeWidth="1" strokeDasharray="3 3" />
                  <circle cx="50%" cy="50%" r="130" fill="none" stroke="#ef4444" strokeWidth="0.5" strokeDasharray="3 3" />
                  <circle cx="50%" cy="50%" r="200" fill="none" stroke="#ef4444" strokeWidth="0.5" strokeDasharray="3 3" />
                  
                  {/* Routes linking center to centers */}
                  {mapData.places.map((place, idx) => {
                    const offsetLat = (place.lat - mapData.center.lat) * 2000;
                    const offsetLon = (place.lon - mapData.center.lon) * 2000;
                    return (
                      <line 
                        key={idx} 
                        x1="50%" 
                        y1="50%" 
                        x2={`calc(50% + ${offsetLon}px)`} 
                        y2={`calc(50% - ${offsetLat}px)`} 
                        stroke="#1e293b" 
                        strokeWidth="1.5" 
                      />
                    )
                  })}
                </svg>

                {/* User Center Node */}
                <div className="absolute w-8 h-8 rounded-full bg-red-600 border-2 border-white flex items-center justify-center shadow-lg shadow-red-600/40 z-20">
                  <User className="w-4.5 h-4.5 text-white" />
                </div>
                
                {/* Seed places pins */}
                {mapData.places.map((place, idx) => {
                  const offsetLat = (place.lat - mapData.center.lat) * 2000;
                  const offsetLon = (place.lon - mapData.center.lon) * 2000;
                  
                  return (
                    <div 
                      key={idx}
                      className="absolute p-2 bg-slate-900 border border-slate-800 hover:border-red-500 rounded-xl flex items-center gap-1.5 cursor-pointer shadow-md group transition-all"
                      style={{
                        top: `calc(50% - ${offsetLat}px - 15px)`,
                        left: `calc(50% + ${offsetLon}px - 20px)`,
                      }}
                    >
                      <div className="w-2.5 h-2.5 bg-red-500 rounded-full group-hover:scale-125 transition-transform" />
                      <span className="text-[10px] font-bold text-white max-w-[60px] truncate">{place.name.split(' ')[0]}</span>
                    </div>
                  )
                })}

                {/* Map stats badges */}
                <div className="absolute bottom-4 left-4 bg-slate-900/90 border border-slate-850 p-3 rounded-xl text-[10px] text-slate-400 space-y-1">
                  <div><strong>City Center:</strong> {mapData.center.lat.toFixed(4)}, {mapData.center.lon.toFixed(4)}</div>
                  <div><strong>Status:</strong> {mapLoading ? 'Loading' : 'Live nearby search'}</div>
                  <div><strong>Source:</strong> {mapData.source || 'Unknown'}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* History details */}
          <div className="lg:col-span-5 space-y-4">
            <div className="glass-panel rounded-3xl p-6 border border-slate-800">
              <h3 className="text-lg font-bold text-white mb-4">Donation Logs</h3>
              <div className="space-y-4">
                <div className="p-4 bg-slate-900/60 rounded-2xl border border-slate-850 flex justify-between items-center">
                  <div>
                    <div className="font-bold text-white text-sm">Lives Saved Index</div>
                    <div className="text-xs text-slate-400 font-light mt-0.5">Calculated using units donated.</div>
                  </div>
                  <div className="text-2xl font-extrabold text-red-500">
                    +{history?.estimated_lives_saved || 0} Lives
                  </div>
                </div>
                <div className="p-4 bg-slate-900/60 rounded-2xl border border-slate-850 flex justify-between items-center">
                  <div>
                    <div className="font-bold text-white text-sm">Last Donation</div>
                    <div className="text-xs text-slate-400 font-light mt-0.5">Date of last blood collection.</div>
                  </div>
                  <div className="text-sm font-bold text-white">
                    {history?.last_donation_date || 'No history recorded'}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Chart Panel */}
          <div className="lg:col-span-7">
            <div className="glass-panel rounded-3xl p-6 border border-slate-800">
              <h3 className="text-lg font-bold text-white mb-6">Donation Statistics</h3>
              <div className="h-[320px] flex items-center justify-center">
                {history?.chart_data ? (
                  <Bar data={getChartJsData()} options={chartOptions} />
                ) : (
                  <span className="text-sm text-slate-500">No stats to render.</span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
