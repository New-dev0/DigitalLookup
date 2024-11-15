import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Container, Row, Col, Card, Form, Button, Navbar, Alert, InputGroup, Collapse, Accordion, Badge, ProgressBar, Toast } from 'react-bootstrap';
import { FaCog, FaSearch, FaChevronDown, FaChevronUp, FaTelegram, FaWhatsapp, FaFacebook, FaInstagram, FaTwitter, FaTimes, FaFileExport, FaFilePdf, FaMoon, FaSun } from 'react-icons/fa';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import ImageSlider from './components/ImageSlider';
import html2canvas from 'html2canvas';
import { jsPDF } from "jspdf";
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';

const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [inputText, setInputText] = useState('');
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showOptions, setShowOptions] = useState(false);


  const [socialInputs, setSocialInputs] = useState({
    telegram: '',
    whatsapp: '',
    whatsappCountryCode: '',
    facebook: '',
    instagram: 'googleindia',
    twitter: ''
  });
  const [searched, setSearched] = useState(false);
  const [searchCompleted, setSearchCompleted] = useState(false);
  const [settings, setSettings] = useState({
    devices: {
      android: true,
      desktop: true
    }
  });

  const { sendMessage, lastMessage, readyState } = useWebSocket(WS_URL, {
    onMessage: handleWebSocketMessage,
  });

  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');

  function handleWebSocketMessage(event) {
    const data = JSON.parse(event.data);
    console.log('Received WebSocket message:', data);
    console.log(data.type);

    switch (data.type) {
      case 'system':
        if (data.status === 'COMPLETED') {
          setResultId(data.resultId);
          setSearchCompleted(true);
        }
        break;
      case 'twitter_report':
        console.log('Twitter report:', data);
        setReport(data.data);
        break;
      case 'global_message':
        setToastMessage(data.data);
        setShowToast(true);
        break;
      default:
        let newData = { ...result } || {};
        if (!newData[data.service]) {
          newData[data.service] = {};
        }
        newData[data.service][data.data.key] = data.data.data;
        console.log('Updated result:', newData);
        setResult(newData);
        setIsLoading(false);
        setSearchCompleted(true);
    }
  }

  const [showImageSlider, setShowImageSlider] = useState(false);
  const [sliderImages, setSliderImages] = useState([]);
  const [initialSlideIndex, setInitialSlideIndex] = useState(0);
  const [report, setReport] = useState();
  const [globalMessage, setGlobalMessage] = useState();
  const [resultId, setResultId] = useState(null);
  const [loadedImages, setLoadedImages] = useState({});

  const imageObserver = useRef(null);

  useEffect(() => {
    imageObserver.current = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const lazyImage = entry.target;
          lazyImage.src = lazyImage.dataset.src;
          lazyImage.classList.remove("lazy");
          observer.unobserve(lazyImage);
        }
      });
    });
  }, []);

  const LazyImage = ({ src, alt, className, style }) => {
    const imgRef = useRef(null);

    useEffect(() => {
      if (imgRef.current && imageObserver.current) {
        imageObserver.current.observe(imgRef.current);
      }
      return () => {
        if (imgRef.current && imageObserver.current) {
          imageObserver.current.unobserve(imgRef.current);
        }
      };
    }, [src]);

    return (
      <img
        ref={imgRef}
        className={`lazy ${className}`}
        data-src={src}
        alt={alt}
        style={{ ...style, backgroundColor: '#f0f0f0' }}
      />
    );
  };

  useEffect(() => {
    if (result) {
      Object.entries(result).forEach(([key, value]) => {
        if (value.images) {
          value.images.forEach((image) => {
            const img = new Image();
            img.src = `${API_URL}/file/${encodeURIComponent(image)}`;
            img.onload = () => {
              setLoadedImages(prev => ({ ...prev, [image]: true }));
            };
          });
        }
      });
    }
  }, [result]);

  const handleSubmit = useCallback((e) => {
    e.preventDefault();
    setIsLoading(true);
    setSearched(true);
    setError(null);
    setResult(null);
    setSearchCompleted(false);

    sendMessage(JSON.stringify({
      action: 'process_request',
      text: inputText,
      socialInputs: socialInputs,
      ...settings
    }));
  }, [inputText, socialInputs, sendMessage, settings]);

  const handleSocialInputChange = (platform, value) => {
    setSocialInputs(prev => ({ ...prev, [platform]: value }));
  };

  const handleSettingChange = (setting, value) => {
    setSettings(prev => ({ ...prev, [setting]: value }));
  };

  const handleDeviceChange = (device, checked) => {
    setSettings(prev => ({
      ...prev,
      devices: {
        ...prev.devices,
        [device]: checked
      }
    }));
  };

  const connectionStatus = {
    [ReadyState.CONNECTING]: 'Connecting',
    [ReadyState.OPEN]: 'Open',
    [ReadyState.CLOSING]: 'Closing',
    [ReadyState.CLOSED]: 'Closed',
    [ReadyState.UNINSTANTIATED]: 'Uninstantiated',
  }[readyState];

  const handleRemoveQuery = () => {
    setResultId(null);
    setSearchCompleted(false);
    setSearched(false);
    setInputText('');
    setResult(null);
    setError(null);
  };

  const getPlatformIcon = (platform) => {
    switch (platform) {
      case 'telegram': return <FaTelegram color="#0088cc" />;
      case 'whatsapp': return <FaWhatsapp color="#25D366" />;
      case 'facebook': return <FaFacebook color="#1877F2" />;
      case 'instagram': return <FaInstagram color="#E4405F" />;
      case 'twitter': return <FaTwitter color="#1DA1F2" />;
      default: return null;
    }
  };

  const handleImageClick = (platform, images, index) => {
    const fullImageUrls = images.map(image => `${API_URL}/file/${encodeURIComponent(image)}`);
    setSliderImages(fullImageUrls);
    setInitialSlideIndex(index);
    setShowImageSlider(true);
  };

  const handleExport = useCallback(() => {
    // Implement export functionality here
    console.log('Exporting data...');
    // You might want to call an API endpoint to generate and download the export
  }, [result]);

  const contentRef = useRef(null);

  const handleSaveAsPDF = useCallback(() => {
    const input = contentRef.current;
    html2canvas(input)
      .then((canvas) => {
        const imgData = canvas.toDataURL('image/png');
        const pdf = new jsPDF();
        const imgProps = pdf.getImageProperties(imgData);
        const pdfWidth = pdf.internal.pageSize.getWidth();
        const pdfHeight = (imgProps.height * pdfWidth) / imgProps.width;
        pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
        pdf.save("digital_lookup_result.pdf");
      });
  }, []);

  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    document.body.classList.toggle('dark-mode', darkMode);
  }, [darkMode]);

  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
  };

  return (
    <div className={`App ${darkMode ? 'dark-mode' : ''}`}>
      <Navbar bg={darkMode ? "dark" : "light"} variant={darkMode ? "dark" : "light"} expand="lg">
        <Container>
          <Navbar.Brand href="#home" style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>DigitalLookup</Navbar.Brand>
          <Button 
            variant={darkMode ? "outline-light" : "outline-dark"} 
            onClick={toggleDarkMode} 
            className="ms-auto"
          >
            {darkMode ? <FaSun /> : <FaMoon />}
          </Button>
        </Container>
      </Navbar>

      <Toast
        show={showToast}
        onClose={() => setShowToast(false)}
        delay={3000}
        autohide
        style={{
          position: 'fixed',
          top: 20,
          right: 20,
          zIndex: 9999
        }}
      >
        <Toast.Header>
          <strong className="me-auto">Notification</strong>
        </Toast.Header>
        <Toast.Body>{toastMessage}</Toast.Body>
      </Toast>

      <div className="settings-icon">
        <FaCog size={24} />
      </div>
      {searchCompleted && <>
        <Container className="mb-3">
          <Row className="justify-content-end">
            <Col xs="auto">
              <Button variant="primary" onClick={handleExport}>
                <FaFileExport className="me-2" />
                Export
              </Button>
              <Button className='m-2' variant="secondary" onClick={handleSaveAsPDF}>
                <FaFilePdf className="me-2" />
                Save Page as PDF
              </Button>
            </Col>
          </Row>
        </Container>
      </>}

      {searched && (
        <Container className="mt-3">
          <Row className="align-items-center">
            <Col>
              <h6>Searched Query:</h6>
              <Badge bg="primary" className="me-2 badge-with-button">
                {inputText}
              </Badge>
              <Badge bg="primary" className="me-2" onClick={handleRemoveQuery}>
                <FaTimes />
              </Badge>
              {Object.entries(socialInputs).map(([platform, value]) =>
                value && (
                  <Badge key={platform} bg="light" text="dark" className="me-2 border">
                    {getPlatformIcon(platform)} {platform}: {value}
                  </Badge>
                )
              )}
            </Col>
          </Row>
        </Container>
      )}

      <div ref={contentRef}>
        {searched ? <>
          {report && (
            <Container className="mt-3 mb-3">
              <Card className="shadow-sm border-0">
                <Card.Header className="bg-primary text-white py-2">
                  <h6 className="mb-0">Report Analysis</h6>
                </Card.Header>
                <Card.Body className="py-2">
                  {['spam_likelihood', 'profanity_detection', 'fraudulent_content_likelihood', 'false_information_probability', 'cyber_fraud_risk', 'drugs_related_content', 'personal_data_exposure']
                    .filter(attribute => report[attribute] !== undefined)
                    .sort((a, b) => report[b] - report[a])
                    .map((attribute, index, array) => {
                      const opacity = 1 - (index / (array.length - 1)) * 0.7; // Decreasing opacity from 1 to 0.3
                      return (
                        <div key={attribute} className="mb-2">
                          <Row className="align-items-center">
                            <Col xs={12} md={4}>
                              <small className="text-muted">{attribute.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}</small>
                            </Col>
                            <Col xs={12} md={8} className="d-flex align-items-center">
                              <ProgressBar
                                now={report[attribute] * 100}
                                style={{ height: "15px", flexGrow: 1, opacity: opacity }}
                                className="me-2"
                                variant="primary"
                              />
                              <small style={{ minWidth: '40px', textAlign: 'right' }}>
                                {`${(report[attribute] * 100).toFixed(1)}%`}
                              </small>
                            </Col>
                          </Row>
                        </div>
                      );
                    })
                  }
                </Card.Body>
                <Card.Footer>
                  {report?.general_message && <p>{report.general_message}</p>}
                </Card.Footer>
              </Card>
            </Container>
          )}
          {result && Object.entries(result).map(([key, value]) => {
            const imagePath = value?.api_data?.image_path;
            const imageUrl = imagePath ? `${API_URL}/file/${encodeURIComponent(imagePath)}` : value?.api_data?.image_url;
            return (
              <Container key={key} className="mb-3">
                <Row>
                  <Col>
                    <Accordion defaultActiveKey="0">
                      <Accordion.Item eventKey="0">
                        <Accordion.Header>
                          {key.charAt(0).toUpperCase() + key.slice(1)}
                        </Accordion.Header>
                        <Accordion.Body>
                          <Container>
                            <Row className="align-items-center">
                              <Col xs={12} md={3} className="text-center mb-2 mb-md-0">
                                {imageUrl && (
                                  <img
                                    src={imageUrl}
                                    alt={value?.api_data?.name}
                                    className="img-fluid rounded-circle"
                                    style={{ maxWidth: '120px', boxShadow: '0 4px 8px rgba(0,0,0,0.1)' }}
                                  />
                                )}
                              </Col>
                              <Col xs={12} md={9}>
                                <h4 className="mb-2 text-primary">{value?.api_data?.name}</h4>
                                <p className="text-muted mb-2">{value?.api_data?.description}</p>
                                {value?.api_data?.followers_count && (
                                  <p className="mb-1">
                                    <strong>Followers:</strong> {value?.api_data?.followers_count.toLocaleString()}
                                  </p>
                                )}
                                {value?.api_data?.following_count && (
                                  <p className="mb-0">
                                    <strong>Following:</strong> {value?.api_data?.following_count.toLocaleString()}
                                  </p>
                                )}
                              </Col>
                            </Row>
                          </Container>
                          <Row className="mt-4">
                            <Col>
                              <div className="d-flex flex-wrap justify-content-start">
                                {value?.images && value.images.map((image, index) => {
                                  const imageUrl = `${API_URL}/file/${encodeURIComponent(image)}`;
                                  const fileName = image.split('\\').pop();
                                  return (
                                    <div key={index} className="m-2" style={{ width: '120px' }} onClick={() => handleImageClick(key, value.images, index)}>
                                      <div style={{ width: '100%', height: '120px', position: 'relative' }}>
                                        <LazyImage
                                          src={imageUrl}
                                          alt={`${key} image ${index + 1}`}
                                          className="img-fluid rounded"
                                          style={{
                                            width: '100%',
                                            height: '100%',
                                            objectFit: 'cover',
                                            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                                          }}
                                        />
                                      </div>
                                      <p className="mt-1 mb-0 text-center" style={{ fontSize: '0.8rem' }}>
                                        {fileName}
                                      </p>
                                    </div>
                                  )
                                })}
                              </div>
                            </Col>
                          </Row>
                          {value?.message && (
                            <Row className="mt-3">
                              <Col>
                                <div className="border rounded p-3" style={{ boxShadow: '0 2px 4px rgba(0,0,0,0.1)', backgroundColor: '#e9ecef' }}>
                                  <p className="mb-0 d-flex align-items-center" style={{ fontFamily: 'Roboto, Arial, sans-serif', fontSize: '0.9rem', color: '#495057' }}>
                                    <span className="mr-2" style={{ fontSize: '1.1rem', color: '#28a745' }}>&#8226;</span>
                                    <strong>Status:</strong>&nbsp;{value?.message}
                                  </p>
                                </div>
                              </Col>
                            </Row>
                          )}

                        </Accordion.Body>
                      </Accordion.Item>
                    </Accordion>
                  </Col>
                </Row>
              </Container>
            )
          })}
          {result && Object.entries(socialInputs).map(([platform, value]) => {
            if (!result[platform] && value) {
              return (
                <Container key={platform} className="mb-3">
                  <Row>
                    <Col>
                      <Accordion defaultActiveKey="0">
                        <Accordion.Item eventKey="0">
                          <Accordion.Header>
                            {platform.charAt(0).toUpperCase() + platform.slice(1)}
                          </Accordion.Header>
                          <Accordion.Body>
                            <div className="d-flex justify-content-center align-items-center" style={{ height: '200px' }}>
                              <div className="spinner-border text-primary" style={{ width: '4rem', height: '4rem' }} role="status">
                                <span className="visually-hidden">Loading...</span>
                              </div>
                            </div>
                          </Accordion.Body>
                        </Accordion.Item>
                      </Accordion>
                    </Col>
                  </Row>
                </Container>
              )
            }
          })}


          {!result && (
            <Container className="d-flex justify-content-center align-items-center" style={{ height: '50vh' }}>
              <div className="spinner-border text-primary" style={{ width: '5rem', height: '5rem' }} role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
            </Container>
          )}
        </> :
          <Container className="d-flex align-items-center justify-content-center" style={{ minHeight: "90vh" }}>
            <Row className="w-100">
              <Col lg={8} className="mx-auto">
                <Card className="mb-3">
                  <Card.Body>
                    <Form onSubmit={handleSubmit}>
                      <Collapse in={!showOptions}>
                        <div>

                          <Form.Group className="mb-3">
                            <InputGroup size="lg">
                              <Form.Control
                                type="text"
                                placeholder="Enter username or link..."
                                value={inputText}
                                onChange={(e) => setInputText(e.target.value)}
                                style={{ fontSize: '1.2rem' }}
                              />
                              <Button variant="outline-secondary" type="submit" disabled={isLoading} style={{ fontSize: '1.2rem' }}>
                                <FaSearch />
                              </Button>
                            </InputGroup>
                          </Form.Group>
                        </div>
                      </Collapse>
                      <Collapse in={showOptions}>
                        <div>
                          <Form.Group className="mb-3">
                            <Row className="mb-2">
                              <Col xs={12} sm={6}>
                                <InputGroup>
                                  <InputGroup.Text>
                                    <FaTelegram color="#0088cc" />
                                  </InputGroup.Text>
                                  <Form.Control
                                    type="text"
                                    placeholder="Telegram username"
                                    value={socialInputs.telegram}
                                    onChange={(e) => handleSocialInputChange('telegram', e.target.value)}
                                  />
                                </InputGroup>
                              </Col>
                              <Col xs={12} sm={6}>
                                <InputGroup>
                                  <InputGroup.Text>
                                    <FaInstagram color="#E4405F" />
                                  </InputGroup.Text>
                                  <Form.Control
                                    type="text"
                                    placeholder="Instagram username"
                                    value={socialInputs.instagram}
                                    onChange={(e) => handleSocialInputChange('instagram', e.target.value)}
                                  />
                                </InputGroup>
                              </Col>
                            </Row>
                            <Row className="mb-2">
                              <Col xs={12} sm={6}>
                                <InputGroup>
                                  <InputGroup.Text>
                                    <FaFacebook color="#1877F2" />
                                  </InputGroup.Text>
                                  <Form.Control
                                    type="text"
                                    placeholder="Facebook username"
                                    value={socialInputs.facebook}
                                    onChange={(e) => handleSocialInputChange('facebook', e.target.value)}
                                  />
                                </InputGroup>
                              </Col>
                              <Col xs={12} sm={6}>
                                <InputGroup>
                                  <InputGroup.Text>
                                    <FaWhatsapp color="#25D366" />
                                  </InputGroup.Text>
                                  <Form.Control
                                    type="text"
                                    placeholder="+1"
                                    value={socialInputs.whatsappCountryCode}

                                    onChange={(e) => {
                                      const value = e.target.value.replace(/[^\d+]/g, '');
                                      handleSocialInputChange('whatsappCountryCode', value);
                                    }}
                                    style={{ flex: '0 0 60px' }}
                                  />

                                  <Form.Control
                                    type="text"
                                    placeholder="Phone number"
                                    value={socialInputs.whatsapp}
                                    onChange={(e) => {
                                      const value = e.target.value.replace(/\D/g, '');
                                      handleSocialInputChange('whatsapp', value);
                                    }}
                                  />
                                </InputGroup>
                              </Col>
                            </Row>
                            <Row>
                              <Col xs={12}>
                                <InputGroup>
                                  <InputGroup.Text>
                                    <FaTwitter color="#1DA1F2" />
                                  </InputGroup.Text>
                                  <Form.Control
                                    type="text"
                                    placeholder="Twitter username"
                                    value={socialInputs.twitter}
                                    onChange={(e) => handleSocialInputChange('twitter', e.target.value)}
                                  />
                                </InputGroup>
                              </Col>
                            </Row>
                          </Form.Group>
                        </div>
                      </Collapse>
                      <div className="d-flex justify-content-end mb-3">
                        <Button
                          variant="link"
                          onClick={() => setShowOptions(!showOptions)}
                          className="text-muted"
                          style={{ fontSize: '0.9rem', textDecoration: 'none' }}
                        >
                          {showOptions ? "Hide options" : "More options"} {showOptions ? <FaChevronUp /> : <FaChevronDown />}
                        </Button>
                      </div>

                      {error && (
                        <Alert variant="danger" className="mt-3">
                          {error}
                        </Alert>
                      )}
                    </Form>
                  </Card.Body>
                  {showOptions && (
                    <Card.Footer className="text-center">
                      <Button
                        variant="primary"
                        type="submit"
                        disabled={isLoading}
                        onClick={handleSubmit}
                        style={{ width: '50%' }}
                      >
                        {isLoading ? 'Analyzing...' : 'Analyze'}
                      </Button>
                    </Card.Footer>
                  )}
                </Card>

                <Accordion className="mb-3">
                  <Accordion.Item eventKey="0">
                    <Accordion.Header>
                      <FaCog className="me-2" /> Settings
                    </Accordion.Header>
                    <Accordion.Body>
                      <Form>
                        <Form.Group className="mt-3">
                          <Form.Label className="text-body">Devices</Form.Label>
                          <div>
                            <Form.Check
                              inline
                              type="checkbox"
                              id="android-checkbox"
                              label={<span className="text-body">Android</span>}
                              checked={settings.devices.android}
                              onChange={(e) => handleDeviceChange('android', e.target.checked)}
                              className="bordered-checkbox"
                            />
                            <Form.Check
                              inline
                              type="checkbox"
                              id="desktop-checkbox"
                              label={<span className="text-body">Desktop</span>}
                              checked={settings.devices.desktop}
                              onChange={(e) => handleDeviceChange('desktop', e.target.checked)}
                              className="bordered-checkbox"
                            />
                          </div>
                        </Form.Group>
                      </Form>
                    </Accordion.Body>
                  </Accordion.Item>
                </Accordion>
              </Col>
            </Row>
          </Container>

        }
      </div>

      <ImageSlider
        images={sliderImages}
        show={showImageSlider}
        onHide={() => setShowImageSlider(false)}
        initialIndex={initialSlideIndex}
      />

      <footer className="websocket-status">
        Connection Status: {connectionStatus}

      </footer>
    </div>
  );
}

export default App;