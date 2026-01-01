import React, { useState, useEffect, useMemo, createRef } from 'react'
import TinderCard from 'react-tinder-card'
import { motion, AnimatePresence } from 'framer-motion'
import './App.css'
import api from './services/api'
import { useAuth } from './context/AuthContext'
import { extractImageAsBase64 } from './utils/imageExtractor'

function App() {
  // Auth
  const { user, token, loading: authLoading, signInWithGoogle, logout, isAuthenticated } = useAuth()
  
  // State
  const [prompt, setPrompt] = useState('')
  const [outfits, setOutfits] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [loading, setLoading] = useState(false)
  const [tryonLoading, setTryonLoading] = useState({})
  const [error, setError] = useState('')
  
  // Usage tracking
  const [usage, setUsage] = useState({ browse_count: 0, tryon_count: 0, browse_limit: 3, tryon_limit: 1 })
  
  // Reveal modal
  const [revealedOutfit, setRevealedOutfit] = useState(null)
  
  // Refs for TinderCard
  const childRefs = useMemo(
    () => Array(outfits.length).fill(0).map(() => createRef()),
    [outfits.length]
  )
  
  // User image upload state
  const [userImageUrl, setUserImageUrl] = useState(null)
  const [userImagePreview, setUserImagePreview] = useState(null)
  const [uploadLoading, setUploadLoading] = useState(false)
  
  // Filters
  const [gender, setGender] = useState('women')
  const [selectedStore, setSelectedStore] = useState('asos')
  const [mixStores, setMixStores] = useState(false)

  // Set auth token when it changes
  useEffect(() => {
    if (token) {
      api.setAuthToken(token)
      // Fetch usage when logged in
      fetchUsage()
    } else {
      api.setAuthToken(null)
    }
  }, [token])

  // Fetch user's usage stats
  const fetchUsage = async () => {
    try {
      const data = await api.getUsage()
      setUsage(data)
    } catch (err) {
      console.error('Failed to fetch usage:', err)
    }
  }

  // Load user image from localStorage
  useEffect(() => {
    const savedImage = localStorage.getItem('userImageUrl')
    const savedPreview = localStorage.getItem('userImagePreview')
    if (savedImage) {
      setUserImageUrl(savedImage)
      setUserImagePreview(savedPreview)
    }
  }, [])

  // Handle Google Sign In
  const handleSignIn = async () => {
    setError('') // Clear previous errors
    const result = await signInWithGoogle()
    if (!result.success) {
      setError(result.error || 'Sign in failed. Please try again.')
    }
  }

  // Handle user image upload
  const handleImageUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      setUserImagePreview(e.target.result)
      localStorage.setItem('userImagePreview', e.target.result)
    }
    reader.readAsDataURL(file)

    setUploadLoading(true)
    try {
      const response = await api.uploadModelImage(file)
      if (response.success) {
        setUserImageUrl(response.image_url)
        localStorage.setItem('userImageUrl', response.image_url)
      }
    } catch (err) {
      console.error('Upload failed:', err)
      setError('Failed to upload image')
    } finally {
      setUploadLoading(false)
    }
  }

  const handleRemoveImage = () => {
    setUserImageUrl(null)
    setUserImagePreview(null)
    localStorage.removeItem('userImageUrl')
    localStorage.removeItem('userImagePreview')
  }

  // Check if user can browse
  const canBrowse = usage.browse_count < usage.browse_limit
  const canTryOn = usage.tryon_count < usage.tryon_limit

  // Browse outfits
  const handleBrowseOutfits = async () => {
    if (!prompt.trim()) {
      setError('Please enter a prompt')
      return
    }

    if (!canBrowse) {
      setError(`You've used all ${usage.browse_limit} searches for today. Come back tomorrow!`)
      return
    }

    setLoading(true)
    setError('')
    
    try {
      const storeToUse = mixStores ? 'mixed' : selectedStore
      const response = await api.browseOutfits(prompt, null, storeToUse, gender)
      
      if (response.success && response.outfits.length > 0) {
        setOutfits(response.outfits)
        setCurrentIndex(response.outfits.length - 1)
        // Refresh usage after successful browse
        fetchUsage()
      } else {
        setError('No outfits found. Try a different prompt.')
      }
    } catch (err) {
      setError(err.message || 'Failed to find outfits. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  // Generate virtual try-on
  const handleGenerateTryOn = async (outfitId, topImageUrl, bottomImageUrl) => {
    if (!canTryOn) {
      setError(`You've used your ${usage.tryon_limit} virtual try-on for today. Come back tomorrow!`)
      return
    }

    setTryonLoading(prev => ({ ...prev, [outfitId]: true }))
    setError('')
    
    try {
      let topBase64 = null
      let bottomBase64 = null
      
      try {
        topBase64 = await extractImageAsBase64(topImageUrl)
      } catch (e) {}
      
      try {
        bottomBase64 = await extractImageAsBase64(bottomImageUrl)
      } catch (e) {}
      
      const response = await api.generateTryOn({
        topImageUrl: topBase64 ? null : topImageUrl,
        bottomImageUrl: bottomBase64 ? null : bottomImageUrl,
        modelImageUrl: userImageUrl,
        topImageBase64: topBase64,
        bottomImageBase64: bottomBase64
      })
      
      if (response.success && response.tryon_image_url) {
        // Update outfits list
        setOutfits(prev => prev.map(outfit => 
          outfit.outfit_id === outfitId 
            ? { ...outfit, tryon_image_url: response.tryon_image_url }
            : outfit
        ))
        // Also update revealed outfit if it's the same one
        setRevealedOutfit(prev => 
          prev && prev.outfit_id === outfitId 
            ? { ...prev, tryon_image_url: response.tryon_image_url }
            : prev
        )
        // Refresh usage after successful try-on
        fetchUsage()
      }
    } catch (err) {
      setError(err.message || 'Failed to generate try-on.')
    } finally {
      setTryonLoading(prev => ({ ...prev, [outfitId]: false }))
    }
  }

  // Handle swipe
  const onSwipe = (direction, outfit, index) => {
    updateCurrentIndex(index - 1)
    api.submitFeedback(outfit.outfit_id, direction === 'right' ? 'like' : 'dislike').catch(() => {})

    if (direction === 'right') {
      setRevealedOutfit(outfit)
    }
  }

  const updateCurrentIndex = (val) => {
    setCurrentIndex(val)
  }

  const swipe = async (dir) => {
    if (currentIndex >= 0 && childRefs[currentIndex]?.current) {
      await childRefs[currentIndex].current.swipe(dir)
    }
  }

  const closeReveal = () => {
    setRevealedOutfit(null)
  }

  // Show loading while checking auth
  if (authLoading) {
    return (
      <div className="app">
        <div className="auth-loading">
          <div className="spinner"></div>
          <p>Loading...</p>
        </div>
      </div>
    )
  }

  // Show login screen if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="app">
        <div className="login-screen">
          <div className="login-card">
            <h1>✨ AI Outfit Recommender</h1>
            <p className="login-subtitle">Discover your perfect style with AI</p>
            
            <div className="login-features">
              <div className="feature">🛍️ Browse ASOS products</div>
              <div className="feature">👗 Virtual try-on with AI</div>
              <div className="feature">💕 Swipe to find your style</div>
            </div>

            <button className="google-login-btn" onClick={handleSignIn}>
              <svg viewBox="0 0 24 24" width="24" height="24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Continue with Google
            </button>

            {error && (
              <div className="login-error">
                ⚠️ {error}
              </div>
            )}

            <p className="login-note">
              Free: 2 outfit searches + 1 virtual try-on every 5 days
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <h1>✨ AI Outfit Recommender</h1>
        <p className="subtitle">Swipe right on outfits you love to see prices & buy!</p>
        
        {/* User info & usage */}
        <div className="user-bar">
          <div className="user-info">
            {user?.photoURL && <img src={user.photoURL} alt="" className="user-avatar" />}
            <span className="user-name">{user?.displayName?.split(' ')[0]}</span>
          </div>
          <div className="usage-info">
            <span className="usage-badge">🔍 {usage.browse_limit - usage.browse_count}/{usage.browse_limit} searches</span>
            <span className="usage-badge">👗 {usage.tryon_limit - usage.tryon_count}/{usage.tryon_limit} try-on</span>
            {usage.days_until_reset && <span className="usage-badge reset-badge">🔄 Resets in {usage.days_until_reset}d</span>}
          </div>
          <button className="logout-btn" onClick={logout}>Logout</button>
        </div>
      </header>

      {/* Prompt Input Section */}
      {!outfits.length && (
        <div className="prompt-section">
          {/* User Image Upload */}
          <div className="upload-section">
            <h3>📸 Your Photo (Optional)</h3>
            <p className="upload-hint">Upload your photo to see outfits on yourself!</p>
            
            <div className="upload-container">
              {userImagePreview ? (
                <div className="user-image-preview">
                  <img src={userImagePreview} alt="Your photo" />
                  <button className="remove-image-btn" onClick={handleRemoveImage}>
                    ✕ Remove
                  </button>
                  <span className="upload-status">✓ Your photo will be used for try-on</span>
                </div>
              ) : (
                <div className="upload-with-example">
                  <div className="example-image-container">
                    <p className="example-label">📌 Example photo:</p>
                    <img 
                      src="https://i.pinimg.com/1200x/17/cd/c1/17cdc121e45e69310685422a7f1455a2.jpg" 
                      alt="Example"
                      className="example-image"
                    />
                    <div className="example-tips">
                      <span>✅ Full body visible</span>
                      <span>✅ Front facing</span>
                      <span>✅ Simple background</span>
                    </div>
                  </div>
                  
                  <label className="upload-label">
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleImageUpload}
                      disabled={uploadLoading}
                      hidden
                    />
                    {uploadLoading ? (
                      <>
                        <div className="spinner-small"></div>
                        Uploading...
                      </>
                    ) : (
                      <>
                        <span className="upload-icon">📷</span>
                        <span>Click to upload your photo</span>
                        <span className="upload-subtext">Like the example shown</span>
                      </>
                    )}
                  </label>
                </div>
              )}
            </div>
          </div>

          {/* Gender Filter */}
          <div className="gender-filter-section">
            <div className="gender-filter">
              <button
                className={`gender-btn ${gender === 'women' ? 'active' : ''}`}
                onClick={() => setGender('women')}
              >
                👩 Women
              </button>
              <button
                className={`gender-btn ${gender === 'men' ? 'active' : ''}`}
                onClick={() => setGender('men')}
              >
                👨 Men
              </button>
            </div>
          </div>

          {/* Stores Selection */}
          <div className="stores-section">
            <h3>🏪 Stores to Browse</h3>
            
            {/* Mix Stores Toggle */}
            <div className="mix-stores-toggle">
              <label className="toggle-label">
                <input
                  type="checkbox"
                  checked={mixStores}
                  onChange={(e) => setMixStores(e.target.checked)}
                />
                <span className="toggle-slider"></span>
                <span className="toggle-text">
                  🔀 Mix Stores
                  <small>Combine products from all stores (e.g., ASOS top + Amazon bottom)</small>
                </span>
              </label>
            </div>
            
            <div className={`stores-grid ${mixStores ? 'stores-mixed-mode' : ''}`}>
              <div 
                className={`store-card selectable ${!mixStores && selectedStore === 'asos' ? 'selected' : ''} ${mixStores ? 'mixed-active' : ''}`}
                onClick={() => !mixStores && setSelectedStore('asos')}
              >
                <div className="store-logo">ASOS</div>
                <span className="store-status available">✓ Available</span>
                {!mixStores && selectedStore === 'asos' && <span className="store-selected-badge">Selected</span>}
                {mixStores && <span className="store-selected-badge mixed">Included</span>}
              </div>
              <div 
                className={`store-card selectable ${!mixStores && selectedStore === 'amazon' ? 'selected' : ''} ${mixStores ? 'mixed-active' : ''}`}
                onClick={() => !mixStores && setSelectedStore('amazon')}
              >
                <div className="store-logo">Amazon</div>
                <span className="store-status available">✓ Available</span>
                {!mixStores && selectedStore === 'amazon' && <span className="store-selected-badge">Selected</span>}
                {mixStores && <span className="store-selected-badge mixed">Included</span>}
              </div>
              <div className="store-card disabled">
                <div className="store-logo">H&M</div>
                <span className="store-status coming-soon">Coming Soon</span>
              </div>
              <div className="store-card disabled">
                <div className="store-logo">Zara</div>
                <span className="store-status coming-soon">Coming Soon</span>
              </div>
              <div className="store-card disabled">
                <div className="store-logo">Myntra</div>
                <span className="store-status coming-soon">Coming Soon</span>
              </div>
              <div className="store-card disabled">
                <div className="store-logo">Flipkart</div>
                <span className="store-status coming-soon">Coming Soon</span>
              </div>
            </div>
            <p className="stores-note">
              {mixStores 
                ? '🔀 Mix mode: Outfits will combine products from ASOS + Amazon!'
                : '💡 Select a store, or enable "Mix Stores" for cross-store combinations!'
              }
            </p>
          </div>

          <div className="prompt-container">
            <input
              type="text"
              className="prompt-input"
              placeholder="e.g., Beach party, colorful and relaxed"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleBrowseOutfits()}
              disabled={loading || !canBrowse}
            />
            <button
              className="generate-btn"
              onClick={handleBrowseOutfits}
              disabled={loading || !canBrowse}
            >
              {loading ? (
                <>
                  <div className="spinner"></div>
                  Searching...
                </>
              ) : !canBrowse ? (
                '🔒 No searches left'
              ) : (
                '🛍️ Find Outfits'
              )}
            </button>
          </div>
          
          {/* Show limit message */}
          {!canBrowse && (
            <div className="limit-message">
              <p>🌙 You've used all your searches!</p>
              <p>Come back in {usage.days_until_reset || 5} days for {usage.browse_limit} more searches.</p>
            </div>
          )}
          
          {error && (
            <div className="error-message">
              <strong>⚠️</strong> {error}
              <button onClick={() => setError('')}>✕</button>
            </div>
          )}

          <div className="examples">
            <p>Try these prompts:</p>
            <div className="example-chips">
              <button onClick={() => setPrompt('Beach party, colorful and relaxed')}>
                🏖️ Beach Party
              </button>
              <button onClick={() => setPrompt('Business meeting, professional')}>
                💼 Business
              </button>
              <button onClick={() => setPrompt('Casual date night, elegant')}>
                ❤️ Date Night
              </button>
              <button onClick={() => setPrompt('Gym workout, sporty')}>
                🏃 Workout
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Swipe Interface */}
      {outfits.length > 0 && (
        <div className="swipe-section">
          <div className="swipe-container">
            <AnimatePresence>
              {outfits.map((outfit, index) => (
                <TinderCard
                  ref={childRefs[index]}
                  key={outfit.outfit_id}
                  className="swipe-card"
                  preventSwipe={['up', 'down']}
                  onSwipe={(dir) => onSwipe(dir, outfit, index)}
                >
                  <motion.div
                    className="card"
                    initial={{ scale: 0.95, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.95, opacity: 0 }}
                  >
                    {outfit.tryon_image_url ? (
                      <div className="outfit-image-container">
                        <img
                          src={outfit.tryon_image_url}
                          alt="Virtual Try-On"
                          className="outfit-image"
                        />
                        <div className="tryon-badge">✨ Virtual Try-On</div>
                      </div>
                    ) : (
                      <div className="product-images-container">
                        <div className="product-image-wrapper">
                          <img
                            src={outfit.combination.top.image_url}
                            alt={outfit.combination.top.name}
                            className="product-image"
                          />
                          <span className="product-label">TOP</span>
                        </div>
                        <div className="product-image-wrapper">
                          <img
                            src={outfit.combination.bottom.image_url}
                            alt={outfit.combination.bottom.name}
                            className="product-image"
                          />
                          <span className="product-label">BOTTOM</span>
                        </div>
                        
                        {/* Virtual Try-On Button */}
                        <button
                          className="tryon-btn"
                          onClick={(e) => {
                            e.stopPropagation()
                            handleGenerateTryOn(
                              outfit.outfit_id,
                              outfit.combination.top.image_url,
                              outfit.combination.bottom.image_url
                            )
                          }}
                          disabled={tryonLoading[outfit.outfit_id] || !canTryOn}
                        >
                          {tryonLoading[outfit.outfit_id] ? (
                            <>
                              <div className="spinner-small"></div>
                              Generating...
                            </>
                          ) : !canTryOn ? (
                            '🔒 Try-on used'
                          ) : (
                            '👗 Try On'
                          )}
                        </button>
                      </div>
                    )}

                    <div className="match-badge">
                      {Math.round(outfit.combination.match_score * 100)}% Match
                    </div>

                    <div className="swipe-hint">
                      <span className="hint-left">✕ Skip</span>
                      <span className="hint-right">♥ Like to see prices</span>
                    </div>
                  </motion.div>
                </TinderCard>
              ))}
            </AnimatePresence>

            {currentIndex < 0 && !revealedOutfit && (
              <div className="no-more-cards">
                <h2>✨ No More Outfits</h2>
                <p>Want to see more?</p>
                <button
                  className="generate-btn"
                  onClick={() => {
                    setOutfits([])
                    setPrompt('')
                  }}
                  disabled={!canBrowse}
                >
                  {canBrowse ? 'Try New Prompt' : '🔒 No searches left'}
                </button>
              </div>
            )}
          </div>

          {currentIndex >= 0 && (
            <div className="button-container">
              <button className="swipe-button dislike" onClick={() => swipe('left')}>
                ✕
              </button>
              <button className="swipe-button like" onClick={() => swipe('right')}>
                ♥
              </button>
            </div>
          )}

          <div className="progress">
            {currentIndex + 1} / {outfits.length} outfits
          </div>
        </div>
      )}

      {/* Reveal Modal */}
      <AnimatePresence>
        {revealedOutfit && (
          <motion.div 
            className="reveal-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closeReveal}
          >
            <motion.div 
              className="reveal-modal"
              initial={{ scale: 0.8, opacity: 0, y: 50 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.8, opacity: 0, y: 50 }}
              onClick={(e) => e.stopPropagation()}
            >
              <button className="reveal-close" onClick={closeReveal}>✕</button>
              
              <div className="reveal-header">
                <h2>❤️ You liked this outfit!</h2>
                <p>Here are the details to buy:</p>
              </div>

              {/* Try-On Button in Reveal Modal */}
              {canTryOn && !revealedOutfit.tryon_image_url && (
                <button
                  className="reveal-tryon-btn"
                  onClick={() => handleGenerateTryOn(
                    revealedOutfit.outfit_id,
                    revealedOutfit.combination.top.image_url,
                    revealedOutfit.combination.bottom.image_url
                  )}
                  disabled={tryonLoading[revealedOutfit.outfit_id]}
                >
                  {tryonLoading[revealedOutfit.outfit_id] ? (
                    <>
                      <div className="spinner-small"></div>
                      Generating Try-On (~30s)...
                    </>
                  ) : (
                    '👗 Virtual Try-On'
                  )}
                </button>
              )}

              {/* Show Try-On Result if available */}
              {revealedOutfit.tryon_image_url && (
                <div className="reveal-tryon-result">
                  <p className="tryon-label">✨ Your Virtual Try-On:</p>
                  <img 
                    src={revealedOutfit.tryon_image_url} 
                    alt="Virtual Try-On"
                    className="reveal-tryon-image"
                  />
                </div>
              )}

              <div className="reveal-products">
                <div className="reveal-product">
                  <img 
                    src={revealedOutfit.combination.top.image_url} 
                    alt={revealedOutfit.combination.top.name}
                  />
                  <div className="reveal-product-info">
                    <h3>{revealedOutfit.combination.top.name}</h3>
                    <p className="reveal-brand">{revealedOutfit.combination.top.brand}</p>
                    <p className="reveal-price">₹{revealedOutfit.combination.top.price.toFixed(2)}</p>
                    <a 
                      href={revealedOutfit.combination.top.buy_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="reveal-buy-btn"
                    >
                      🛒 Buy Top
                    </a>
                  </div>
                </div>

                <div className="reveal-product">
                  <img 
                    src={revealedOutfit.combination.bottom.image_url} 
                    alt={revealedOutfit.combination.bottom.name}
                  />
                  <div className="reveal-product-info">
                    <h3>{revealedOutfit.combination.bottom.name}</h3>
                    <p className="reveal-brand">{revealedOutfit.combination.bottom.brand}</p>
                    <p className="reveal-price">₹{revealedOutfit.combination.bottom.price.toFixed(2)}</p>
                    <a 
                      href={revealedOutfit.combination.bottom.buy_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="reveal-buy-btn"
                    >
                      🛒 Buy Bottom
                    </a>
                  </div>
                </div>
              </div>

              <div className="reveal-total">
                <span>Total Outfit Price:</span>
                <span className="total-amount">₹{revealedOutfit.combination.total_price.toFixed(2)}</span>
              </div>

              <button className="reveal-continue" onClick={closeReveal}>
                Continue Swiping →
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Footer */}
      <footer className="footer">
        <p>Made with ❤️ using AI</p>
      </footer>
    </div>
  )
}

export default App
