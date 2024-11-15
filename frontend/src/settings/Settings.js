import React, { useState } from 'react';
import { Container, Navbar, Row, Col, ToggleButtonGroup, ToggleButton, Form } from 'react-bootstrap';
import "../App.css";

function Settings() {
    const [activeSection, setActiveSection] = useState('general');
    const [proxySettings, setProxySettings] = useState('');

    const renderInnerSettings = () => {
        switch (activeSection) {
            case 'general':
                return (
                    <>
                        <h4>General Settings</h4>
                        <Form.Group className="mt-3">
                            <Form.Label>Proxy Settings</Form.Label>
                            <Form.Control 
                                as="textarea" 
                                rows={3} 
                                value={proxySettings}
                                onChange={(e) => setProxySettings(e.target.value)}
                                placeholder="Enter proxy settings here..."
                            />
                        </Form.Group>
                    </>
                );
            case 'account':
                return <h4>Account Settings</h4>;
            case 'privacy':
                return <h4>Privacy Settings</h4>;
            default:
                return null;
        }
    };

    return (
        <Container fluid className="px-0">
            <Navbar bg="light" expand="lg" className="mb-4 shadow-sm">
                <Container>
                    <Navbar.Brand href="/" style={{ fontSize: '1.3rem', fontWeight: 'bold' }}>DigitalLookup</Navbar.Brand>
                </Container>
            </Navbar>
            <Container>
                <Row>
                    <Col md={3} className="mb-4">
                        <ToggleButtonGroup type="radio" name="settings-options" vertical className="w-100">
                            <ToggleButton 
                                id="general" 
                                value="general" 
                                variant={activeSection === 'general' ? 'secondary' : 'outline-secondary'}
                                onClick={() => setActiveSection('general')}
                                className="text-start py-3 mb-2 shadow"
                            >
                                General
                            </ToggleButton>
                            <ToggleButton 
                                id="account" 
                                value="account" 
                                variant={activeSection === 'account' ? 'secondary' : 'outline-secondary'}
                                onClick={() => setActiveSection('account')}
                                className="text-start py-3 mb-2 shadow"
                            >
                                Account
                            </ToggleButton>
                            <ToggleButton 
                                id="privacy" 
                                value="privacy" 
                                variant={activeSection === 'privacy' ? 'secondary' : 'outline-secondary'}
                                onClick={() => setActiveSection('privacy')}
                                className="text-start py-3 mb-2 shadow"
                            >
                                Privacy
                            </ToggleButton>
                        </ToggleButtonGroup>
                    </Col>
                    <Col md={8} className="bg-white p-4 rounded shadow-sm">
                        {renderInnerSettings()}
                    </Col>
                </Row>
            </Container>
        </Container>        
    );
}

export default Settings;