import React from 'react';
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';
import { Navbar, Container } from 'react-bootstrap';
import { FaCog } from 'react-icons/fa';
import Home from './Home';
import Settings from './settings/Settings';
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App" style={{
        backgroundColor: "#e6f2ff",
        minHeight: "100vh",
      }}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
