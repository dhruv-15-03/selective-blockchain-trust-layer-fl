import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Nav from './components/Nav'
import Home from './pages/Home'
import Run from './pages/Run'
import Dashboard from './pages/Dashboard'
import Demo from './pages/Demo'
import Results from './pages/Results'
import UpworkCreate from './pages/UpworkCreate'
import UpworkSubmitProof from './pages/UpworkSubmitProof'
import UpworkRunAI from './pages/UpworkRunAI'
import UpworkDecision from './pages/UpworkDecision'
import UpworkResults from './pages/UpworkResults'
import Login from './pages/Login'
import SignUp from './pages/SignUp'
import Profile from './pages/Profile'
import './App.css'

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-wrap">
        <Nav />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/run" element={<Run />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/demo" element={<Demo />} />
          <Route path="/results" element={<Results />} />
          <Route path="/upwork/create" element={<UpworkCreate />} />
          <Route path="/upwork/submit_proof" element={<UpworkSubmitProof />} />
          <Route path="/upwork/run_ai" element={<UpworkRunAI />} />
          <Route path="/upwork/decision" element={<UpworkDecision />} />
          <Route path="/upwork/results" element={<UpworkResults />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<SignUp />} />
          <Route path="/profile" element={<Profile />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
