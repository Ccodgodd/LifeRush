import React, { useState } from 'react';
import { Heart, Activity, Shield, Users, LogIn, UserPlus, Upload, FileText, CheckCircle, HelpCircle } from 'lucide-react';

export default function LandingPage({ onLoginSuccess }) {
  const [isLogin, setIsLogin] = useState(true);
  const [showForgot, setShowForgot] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    phone: '',
    role: 'donor',
    blood_group: '',
    city: '',
    state: '',
    new_password: ''
  });
  
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const parseResponse = async (response) => {
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      return response.json();
    }

    const text = await response.text();
    return { detail: text || `Request failed with status ${response.status}` };
  };

  const handleInputChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      const submitData = new URLSearchParams();
      submitData.append('username', formData.email);
      submitData.append('password', formData.password);

      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: submitData.toString()
      });
      const data = await parseResponse(response);
      if (!response.ok) throw new Error(data.detail || 'Login failed');
      
      setSuccess('Logged in successfully!');
      setTimeout(() => {
        onLoginSuccess(data);
      }, 800);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const submitData = new FormData();
      submitData.append('email', formData.email);
      submitData.append('password', formData.password);
      submitData.append('name', formData.name);
      submitData.append('phone', formData.phone);
      submitData.append('role', formData.role);
      submitData.append('city', formData.city);
      submitData.append('state', formData.state);
      if (formData.blood_group) {
        submitData.append('blood_group', formData.blood_group);
      }
      if (file) {
        submitData.append('report', file);
      }

      const response = await fetch('/api/v1/auth/register', {
        method: 'POST',
        body: submitData,
      });

      const data = await parseResponse(response);
      if (!response.ok) throw new Error(data.detail || 'Registration failed');

      setSuccess('Registration successful! You can now log in.');
      setIsLogin(true);
      // clear fields
      setFormData({
        ...formData,
        name: '',
        phone: '',
        blood_group: '',
        city: '',
        state: ''
      });
      setFile(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      const response = await fetch('/api/v1/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: formData.email, new_password: formData.new_password })
      });
      const data = await parseResponse(response);
      if (!response.ok) throw new Error(data.detail || 'Failed to update password');
      setSuccess('Password updated successfully. Login with your new password.');
      setShowForgot(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative flex flex-col items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      {/* Background glow effects */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-red-600/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-red-950/20 rounded-full blur-[120px] pointer-events-none" />
      
      <div className="max-w-6xl w-full grid grid-cols-1 lg:grid-cols-12 gap-12 items-center relative z-10">
        
        {/* Left Side: Brand & Marketing Info */}
        <div className="lg:col-span-7 space-y-8 text-left">
          <div className="flex items-center gap-3">
            <div className="bg-red-600 p-3 rounded-2xl shadow-lg shadow-red-500/20 animate-pulse-slow">
              <Heart className="w-8 h-8 text-white fill-white" />
            </div>
            <span className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-100 to-red-400 bg-clip-text text-transparent">
              LifeRush AI
            </span>
          </div>

          <div className="space-y-4">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-none">
              Connecting the right donor to the patient <span className="text-red-500 bg-gradient-to-r from-red-500 to-red-400 bg-clip-text">in minutes.</span>
            </h1>
            <p className="text-lg text-slate-400 max-w-xl font-light">
              LifeRush AI utilizes Computer Vision, smart geospatial matching algorithms, and automated telephony notifications to link critical blood requirements to eligible donors instantly.
            </p>
          </div>

          {/* Core App Features List */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-4">
            <div className="flex gap-4 items-start">
              <div className="p-2 bg-red-950/30 rounded-xl border border-red-500/20 text-red-500">
                <Activity className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-white font-medium">AI Report Analysis</h4>
                <p className="text-sm text-slate-400">Upload reports to instantly check hemoglobin & eligibility metrics.</p>
              </div>
            </div>
            <div className="flex gap-4 items-start">
              <div className="p-2 bg-red-950/30 rounded-xl border border-red-500/20 text-red-500">
                <Shield className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-white font-medium">Smart Match Score</h4>
                <p className="text-sm text-slate-400">Blends distance, compatibility, and availability scoring.</p>
              </div>
            </div>
            <div className="flex gap-4 items-start">
              <div className="p-2 bg-red-950/30 rounded-xl border border-red-500/20 text-red-500">
                <Users className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-white font-medium">Automated IVR Calling</h4>
                <p className="text-sm text-slate-400">Initiates automated donor alerts & updates response ETAs.</p>
              </div>
            </div>
            <div className="flex gap-4 items-start">
              <div className="p-2 bg-red-950/30 rounded-xl border border-red-500/20 text-red-500">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-white font-medium">24/7 AI Guidance</h4>
                <p className="text-sm text-slate-400">Interact with an AI assistant to clear all donation criteria.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Authentication Panel */}
        <div className="lg:col-span-5 w-full">
          <div className="glass-panel rounded-3xl p-8 border border-slate-800 shadow-2xl relative">
            
            {/* Header Switch Tabs */}
            {!showForgot && (
              <div className="flex rounded-xl bg-slate-900/60 p-1 mb-8 border border-slate-800/80">
                <button
                  onClick={() => { setIsLogin(true); setError(''); setSuccess(''); }}
                  className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm font-medium rounded-lg transition-all ${
                    isLogin ? 'bg-red-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <LogIn className="w-4 h-4" />
                  Sign In
                </button>
                <button
                  onClick={() => { setIsLogin(false); setError(''); setSuccess(''); }}
                  className={`flex-1 flex items-center justify-center gap-2 py-2 text-sm font-medium rounded-lg transition-all ${
                    !isLogin ? 'bg-red-600 text-white shadow-md' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <UserPlus className="w-4 h-4" />
                  Register
                </button>
              </div>
            )}

            {/* Error and Success Indicators */}
            {error && (
              <div className="mb-6 p-4 rounded-xl bg-red-950/30 border border-red-800 text-red-400 text-sm">
                {error}
              </div>
            )}
            {success && (
              <div className="mb-6 p-4 rounded-xl bg-green-950/30 border border-green-800 text-green-400 text-sm flex gap-2 items-center">
                <CheckCircle className="w-4 h-4" />
                {success}
              </div>
            )}

            {showForgot ? (
              /* Forgot Password Form */
              <form onSubmit={handleForgotPassword} className="space-y-6">
                <div>
                  <h3 className="text-xl font-bold text-white mb-2">Reset Password</h3>
                  <p className="text-slate-400 text-xs mb-6">Enter your registered email and your new desired password.</p>
                </div>
                <div>
                  <label className="block text-slate-300 text-xs font-semibold uppercase mb-2">Email Address</label>
                  <input
                    type="email"
                    name="email"
                    required
                    value={formData.email}
                    onChange={handleInputChange}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:outline-none focus:border-red-500"
                    placeholder="email@example.com"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 text-xs font-semibold uppercase mb-2">New Password</label>
                  <input
                    type="password"
                    name="new_password"
                    required
                    value={formData.new_password}
                    onChange={handleInputChange}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:outline-none focus:border-red-500"
                    placeholder="••••••••"
                  />
                </div>
                <div className="flex gap-4 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowForgot(false)}
                    className="flex-1 border border-slate-800 hover:bg-slate-900 text-slate-400 py-3 rounded-xl text-sm font-medium transition-all"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={loading}
                    className="flex-1 bg-red-600 hover:bg-red-500 text-white py-3 rounded-xl text-sm font-medium transition-all shadow-lg shadow-red-500/20"
                  >
                    {loading ? 'Updating...' : 'Update Password'}
                  </button>
                </div>
              </form>
            ) : isLogin ? (
              /* Login Form */
              <form onSubmit={handleLoginSubmit} className="space-y-6">
                <div>
                  <label className="block text-slate-300 text-xs font-semibold uppercase mb-2">Email Address</label>
                  <input
                    type="email"
                    name="email"
                    required
                    value={formData.email}
                    onChange={handleInputChange}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:outline-none focus:border-red-500"
                    placeholder="email@example.com"
                  />
                </div>
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="text-slate-300 text-xs font-semibold uppercase">Password</label>
                    <button
                      type="button"
                      onClick={() => setShowForgot(true)}
                      className="text-xs text-red-500 hover:underline"
                    >
                      Forgot?
                    </button>
                  </div>
                  <input
                    type="password"
                    name="password"
                    required
                    value={formData.password}
                    onChange={handleInputChange}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:outline-none focus:border-red-500"
                    placeholder="••••••••"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-red-600 hover:bg-red-500 text-white py-3.5 rounded-xl font-semibold transition-all shadow-lg shadow-red-500/20"
                >
                  {loading ? 'Signing In...' : 'Sign In'}
                </button>
              </form>
            ) : (
              /* Registration Form */
              <form onSubmit={handleRegisterSubmit} className="space-y-5">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-slate-300 text-xs font-semibold uppercase mb-1.5">Full Name</label>
                    <input
                      type="text"
                      name="name"
                      required
                      value={formData.name}
                      onChange={handleInputChange}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-white placeholder-slate-600 focus:outline-none focus:border-red-500 text-sm"
                      placeholder="John Doe"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-300 text-xs font-semibold uppercase mb-1.5">Phone Number</label>
                    <input
                      type="text"
                      name="phone"
                      required
                      value={formData.phone}
                      onChange={handleInputChange}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-white placeholder-slate-600 focus:outline-none focus:border-red-500 text-sm"
                      placeholder="123-456-7890"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-slate-300 text-xs font-semibold uppercase mb-1.5">Email</label>
                    <input
                      type="email"
                      name="email"
                      required
                      value={formData.email}
                      onChange={handleInputChange}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-white placeholder-slate-600 focus:outline-none focus:border-red-500 text-sm"
                      placeholder="email@site.com"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-300 text-xs font-semibold uppercase mb-1.5">Password</label>
                    <input
                      type="password"
                      name="password"
                      required
                      value={formData.password}
                      onChange={handleInputChange}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-white placeholder-slate-600 focus:outline-none focus:border-red-500 text-sm"
                      placeholder="••••••••"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-1">
                    <label className="block text-slate-300 text-xs font-semibold uppercase mb-1.5">Blood Group</label>
                    <select
                      name="blood_group"
                      value={formData.blood_group}
                      onChange={handleInputChange}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-white focus:outline-none focus:border-red-500 text-xs"
                    >
                      <option value="">Select</option>
                      <option value="O+">O+</option>
                      <option value="O-">O-</option>
                      <option value="A+">A+</option>
                      <option value="A-">A-</option>
                      <option value="B+">B+</option>
                      <option value="B-">B-</option>
                      <option value="AB+">AB+</option>
                      <option value="AB-">AB-</option>
                    </select>
                  </div>
                  <div className="col-span-1">
                    <label className="block text-slate-300 text-xs font-semibold uppercase mb-1.5">City</label>
                    <input
                      type="text"
                      name="city"
                      required
                      value={formData.city}
                      onChange={handleInputChange}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-white placeholder-slate-600 focus:outline-none focus:border-red-500 text-sm"
                      placeholder="SF"
                    />
                  </div>
                  <div className="col-span-1">
                    <label className="block text-slate-300 text-xs font-semibold uppercase mb-1.5">State</label>
                    <input
                      type="text"
                      name="state"
                      required
                      value={formData.state}
                      onChange={handleInputChange}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-white placeholder-slate-600 focus:outline-none focus:border-red-500 text-sm"
                      placeholder="CA"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-slate-300 text-xs font-semibold uppercase mb-1.5">Your Role</label>
                  <div className="grid grid-cols-2 gap-4">
                    <label className={`flex items-center gap-2 border rounded-xl p-3 cursor-pointer transition-all ${
                      formData.role === 'donor' ? 'border-red-500 bg-red-950/20 text-white' : 'border-slate-850 bg-slate-900/50 text-slate-400 hover:text-slate-300'
                    }`}>
                      <input
                        type="radio"
                        name="role"
                        value="donor"
                        checked={formData.role === 'donor'}
                        onChange={handleInputChange}
                        className="accent-red-500"
                      />
                      <span className="text-sm font-medium">Donor</span>
                    </label>
                    <label className={`flex items-center gap-2 border rounded-xl p-3 cursor-pointer transition-all ${
                      formData.role === 'patient' ? 'border-red-500 bg-red-950/20 text-white' : 'border-slate-850 bg-slate-900/50 text-slate-400 hover:text-slate-300'
                    }`}>
                      <input
                        type="radio"
                        name="role"
                        value="patient"
                        checked={formData.role === 'patient'}
                        onChange={handleInputChange}
                        className="accent-red-500"
                      />
                      <span className="text-sm font-medium">Patient / Hospital</span>
                    </label>
                  </div>
                </div>

                {formData.role === 'donor' && (
                  <div>
                    <label className="block text-slate-300 text-xs font-semibold uppercase mb-2">
                      Medical Report <span className="text-slate-500">(PDF/JPG/PNG - for eligibility OCR)</span>
                    </label>
                    <label className="flex flex-col items-center justify-center border border-dashed border-slate-850 rounded-xl px-4 py-4 cursor-pointer hover:bg-slate-900/30 transition-all">
                      <Upload className="w-5 h-5 text-slate-400 mb-1" />
                      <span className="text-xs text-slate-400 font-medium">
                        {file ? file.name : 'Select or drop medical file'}
                      </span>
                      <input
                        type="file"
                        accept="image/*,application/pdf,.txt"
                        className="hidden"
                        onChange={handleFileChange}
                      />
                    </label>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-red-600 hover:bg-red-500 text-white py-3 rounded-xl font-semibold transition-all shadow-lg shadow-red-500/20"
                >
                  {loading ? 'Creating Account...' : 'Complete Register'}
                </button>
              </form>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
