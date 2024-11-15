import React, { useState } from 'react';
import { Modal, Carousel } from 'react-bootstrap';
import { FaTimes, FaChevronLeft, FaChevronRight, FaDownload } from 'react-icons/fa';

const ImageSlider = ({ images, show, onHide, initialIndex = 0 }) => {
  const [index, setIndex] = useState(initialIndex);

  const handleSelect = (selectedIndex) => {
    setIndex(selectedIndex);
  };

  const getFileName = (path) => {
    return decodeURIComponent(path).split('\\').pop().split('/').pop();
  };

  const handleSaveImage = () => {
    const currentImage = images[index];
    const link = document.createElement('a');
    link.href = currentImage;
    link.download = getFileName(currentImage);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <Modal show={show} onHide={onHide} size="lg" centered>
      <Modal.Header closeButton>
        <Modal.Title>Image {index + 1} of {images.length}</Modal.Title>
      </Modal.Header>
      <Modal.Body className="p-0">
        <Carousel 
          activeIndex={index} 
          onSelect={handleSelect} 
          interval={null}
          prevIcon={<div className="carousel-control-prev-icon custom"><FaChevronLeft color="black" /></div>}
          nextIcon={<div className="carousel-control-next-icon custom"><FaChevronRight color="black" /></div>}
        >
          {images.map((image, idx) => (
            <Carousel.Item key={idx}>
              <div className="d-flex align-items-center justify-content-center" style={{ height: 'calc(100vh - 132px)' }}>
                <img
                  className="d-block"
                  src={image}
                  alt={`Slide ${idx + 1}`}
                  style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
                />
              </div>
              <Carousel.Caption>
                <h3>{getFileName(image)}</h3>
              </Carousel.Caption>
            </Carousel.Item>
          ))}
        </Carousel>
      </Modal.Body>
      <Modal.Footer>
        <button className="btn btn-primary me-2" onClick={handleSaveImage}>
          <FaDownload /> Save Image
        </button>
        <button className="btn btn-secondary" onClick={onHide}>
          <FaTimes /> Close
        </button>
      </Modal.Footer>
    </Modal>
  );
};

export default ImageSlider;