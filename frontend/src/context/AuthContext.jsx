import React, { createContext, useContext, useState, useEffect } from 'react';
import { 
  signInWithPopup, 
  signOut, 
  onAuthStateChanged 
} from 'firebase/auth';
import { auth, googleProvider } from '../config/firebase';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(null);

  // Listen for auth state changes
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        // Get the ID token to send to backend
        const idToken = await user.getIdToken();
        setToken(idToken);
        setUser({
          uid: user.uid,
          email: user.email,
          displayName: user.displayName,
          photoURL: user.photoURL
        });
      } else {
        setUser(null);
        setToken(null);
      }
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  // Refresh token periodically (Firebase tokens expire after 1 hour)
  useEffect(() => {
    if (!user) return;

    const refreshToken = async () => {
      try {
        const newToken = await auth.currentUser?.getIdToken(true);
        if (newToken) setToken(newToken);
      } catch (err) {
        console.error('Token refresh failed:', err);
      }
    };

    // Refresh every 50 minutes
    const interval = setInterval(refreshToken, 50 * 60 * 1000);
    return () => clearInterval(interval);
  }, [user]);

  const signInWithGoogle = async () => {
    try {
      console.log('🔐 Starting Google sign-in...');
      const result = await signInWithPopup(auth, googleProvider);
      console.log('✅ Sign-in successful:', result.user.email);
      return { success: true, user: result.user };
    } catch (error) {
      console.error('❌ Google sign-in error:', error.code, error.message);
      
      // Handle specific Firebase errors
      if (error.code === 'auth/popup-closed-by-user') {
        return { success: false, error: 'Sign-in popup was closed. Please try again.' };
      }
      if (error.code === 'auth/popup-blocked') {
        return { success: false, error: 'Popup was blocked. Please allow popups for this site.' };
      }
      if (error.code === 'auth/unauthorized-domain') {
        return { success: false, error: 'This domain is not authorized in Firebase. Add localhost to authorized domains.' };
      }
      
      return { success: false, error: error.message };
    }
  };

  const logout = async () => {
    try {
      await signOut(auth);
      return { success: true };
    } catch (error) {
      console.error('Logout error:', error);
      return { success: false, error: error.message };
    }
  };

  const value = {
    user,
    token,
    loading,
    signInWithGoogle,
    logout,
    isAuthenticated: !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

