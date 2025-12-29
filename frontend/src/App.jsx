import { useState, useEffect } from 'react'
import TinderCard from 'react-tinder-card'
import { motion, AnimatePresence } from 'framer-motion'
import './App.css'
import api from './services/api'

function App() {
  // State
  const [prompt, setPrompt] = useState('')
  const [outfits, setOutfits] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [likedOutfits, setLikedOutfits] = useState([])
  const [showLiked, setShowLiked] = useState(false)

  // Load liked outfits from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('likedOutfits')
    if (saved) {
      setLikedOutfits(JSON.parse(saved))
    }
  }, [])

  // Generate outfits from prompt
  const handleGenerateOutfits = async () => {
    if (!prompt.trim()) {
      setError('Please enter a prompt')
      return
    }

    setLoading(true)
    setError('')
    
    try {
      const response = await api.generateOutfits(prompt)
      
      if (response.success && response.outfits.length > 0) {
        setOutfits(response.outfits)
        setCurrentIndex(response.outfits.length - 1)
      } else {
        setError('No outfits found. Try a different prompt.')
      }
    } catch (err) {
      setError(err.message || 'Failed to generate outfits. Please try again.')
      console.error('Error generating outfits:', err)
    } finally {
      setLoading(false)
    }
  }

  // Handle swipe
  const onSwipe = async (direction, outfit) => {
    console.log(`Swiped ${direction} on outfit ${outfit.outfit_id}`)
    
    // Record feedback
    const action = direction === 'right' ? 'like' : direction === 'left' ? 'dislike' : 'skip'
    
    try {
      await api.submitFeedback(outfit.outfit_id, action)
    } catch (err) {
      console.error('Failed to submit feedback:', err)
    }

    // If liked, save to liked list
    if (direction === 'right') {
      const newLiked = [...likedOutfits, outfit]
      setLikedOutfits(newLiked)
      localStorage.setItem('likedOutfits', JSON.stringify(newLiked))
    }
  }

  // Handle card leaving screen
  const onCardLeftScreen = (outfitId) => {
    console.log(`Outfit ${outfitId} left screen`)
  }

  // Current outfit
  const currentOutfit = outfits[currentIndex]

  // Manual swipe buttons
  const swipe = (dir) => {
    if (currentIndex >= 0) {
      const outfit = outfits[currentIndex]
      onSwipe(dir, outfit)
      setCurrentIndex(currentIndex - 1)
    }
  }

  // Remove from liked
  const removeFromLiked = (outfitId) => {
    const updated = likedOutfits.filter(o => o.outfit_id !== outfitId)
    setLikedOutfits(updated)
    localStorage.setItem('likedOutfits', JSON.stringify(updated))
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <h1>✨ AI Outfit Recommender</h1>
        <p className="subtitle">Describe your style, we'll create the perfect look</p>
      </header>

      {/* Prompt Input */}
      {!outfits.length && (
        <div className="prompt-section">
          <div className="prompt-container">
            <input
              type="text"
              className="prompt-input"
              placeholder="e.g., Beach party, colorful and relaxed"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleGenerateOutfits()}
              disabled={loading}
            />
            <button
              className="generate-btn"
              onClick={handleGenerateOutfits}
              disabled={loading}
            >
              {loading ? (
                <>
                  <div className="spinner"></div>
                  Generating...
                </>
              ) : (
                'Generate Outfits'
              )}
            </button>
          </div>
          
          {error && (
            <div className="error-message">
              ⚠️ {error}
            </div>
          )}

          <div className="examples">
            <p>Try these prompts:</p>
            <div className="example-chips">
              <button onClick={() => setPrompt('Beach party, colorful and relaxed')}>
                🏖️ Beach Party
              </button>
              <button onClick={() => setPrompt('Business meeting, professional and confident')}>
                💼 Business Meeting
              </button>
              <button onClick={() => setPrompt('Casual date night, romantic and elegant')}>
                ❤️ Date Night
              </button>
              <button onClick={() => setPrompt('Gym workout, comfortable and sporty')}>
                🏃 Gym Workout
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Swipe Interface */}
      {outfits.length > 0 && !showLiked && (
        <div className="swipe-section">
          <div className="swipe-container">
            <AnimatePresence>
              {outfits.map((outfit, index) => (
                <TinderCard
                  key={outfit.outfit_id}
                  className="swipe-card"
                  preventSwipe={['up', 'down']}
                  onSwipe={(dir) => onSwipe(dir, outfit)}
                  onCardLeftScreen={() => onCardLeftScreen(outfit.outfit_id)}
                >
                  <motion.div
                    className="card"
                    initial={{ scale: 0.95, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.95, opacity: 0 }}
                  >
                    {/* Outfit Image */}
                    <div className="outfit-image-container">
                      <img
                        src={outfit.tryon_image_url}
                        alt="Outfit"
                        className="outfit-image"
                      />
                      
                      {/* Match Score Badge */}
                      <div className="match-badge">
                        {Math.round(outfit.combination.match_score * 100)}% Match
                      </div>
                    </div>

                    {/* Outfit Details */}
                    <div className="outfit-details">
                      <div className="product-item">
                        <div className="product-info">
                          <h3>{outfit.combination.top.name}</h3>
                          <p className="brand">{outfit.combination.top.brand || 'Generic'}</p>
                          <p className="price">₹{outfit.combination.top.price.toFixed(2)}</p>
                        </div>
                        <a
                          href={outfit.combination.top.buy_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="buy-btn"
                          onClick={(e) => e.stopPropagation()}
                        >
                          Buy Top
                        </a>
                      </div>

                      <div className="product-item">
                        <div className="product-info">
                          <h3>{outfit.combination.bottom.name}</h3>
                          <p className="brand">{outfit.combination.bottom.brand || 'Generic'}</p>
                          <p className="price">₹{outfit.combination.bottom.price.toFixed(2)}</p>
                        </div>
                        <a
                          href={outfit.combination.bottom.buy_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="buy-btn"
                          onClick={(e) => e.stopPropagation()}
                        >
                          Buy Bottom
                        </a>
                      </div>

                      <div className="total-price">
                        <strong>Total:</strong> ₹{outfit.combination.total_price.toFixed(2)}
                      </div>
                    </div>
                  </motion.div>
                </TinderCard>
              ))}
            </AnimatePresence>

            {/* No more cards */}
            {currentIndex < 0 && (
              <div className="no-more-cards">
                <h2>✨ No More Outfits</h2>
                <p>Want to see more?</p>
                <button
                  className="generate-btn"
                  onClick={() => {
                    setOutfits([])
                    setPrompt('')
                  }}
                >
                  Try New Prompt
                </button>
              </div>
            )}
          </div>

          {/* Swipe Buttons */}
          {currentIndex >= 0 && (
            <div className="button-container">
              <button
                className="swipe-button dislike"
                onClick={() => swipe('left')}
              >
                ✕
              </button>
              <button
                className="swipe-button like"
                onClick={() => swipe('right')}
              >
                ♥
              </button>
            </div>
          )}

          {/* Progress */}
          <div className="progress">
            {currentIndex + 1} / {outfits.length} outfits remaining
          </div>

          {/* View Liked Button */}
          {likedOutfits.length > 0 && (
            <button
              className="view-liked-btn"
              onClick={() => setShowLiked(true)}
            >
              ❤️ View Liked ({likedOutfits.length})
            </button>
          )}
        </div>
      )}

      {/* Liked Outfits */}
      {showLiked && (
        <div className="liked-section">
          <div className="liked-header">
            <h2>❤️ Your Liked Outfits</h2>
            <button
              className="close-btn"
              onClick={() => setShowLiked(false)}
            >
              ✕ Close
            </button>
          </div>

          <div className="liked-grid">
            {likedOutfits.map((outfit) => (
              <div key={outfit.outfit_id} className="liked-card">
                <img
                  src={outfit.tryon_image_url}
                  alt="Liked outfit"
                  className="liked-image"
                />
                <div className="liked-details">
                  <p className="liked-prompt">{outfit.prompt}</p>
                  <p className="liked-price">₹{outfit.combination.total_price.toFixed(2)}</p>
                  <div className="liked-actions">
                    <a
                      href={outfit.combination.top.buy_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="buy-btn-small"
                    >
                      Buy Top
                    </a>
                    <a
                      href={outfit.combination.bottom.buy_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="buy-btn-small"
                    >
                      Buy Bottom
                    </a>
                  </div>
                  <button
                    className="remove-btn"
                    onClick={() => removeFromLiked(outfit.outfit_id)}
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>

          {likedOutfits.length === 0 && (
            <div className="no-liked">
              <p>No liked outfits yet. Start swiping!</p>
            </div>
          )}
        </div>
      )}

      {/* Footer */}
      <footer className="footer">
        <p>Made with ❤️ using AI</p>
      </footer>
    </div>
  )
}

export default App
