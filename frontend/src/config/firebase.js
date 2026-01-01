import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyBJwYJTGpwaZI056kJoT4Gp6g1EmZkDOYM",
  authDomain: "outfit-planner-ca620.firebaseapp.com",
  projectId: "outfit-planner-ca620",
  storageBucket: "outfit-planner-ca620.firebasestorage.app",
  messagingSenderId: "750849889670",
  appId: "1:750849889670:web:f03971e0596462fca40807",
  measurementId: "G-HHWXP9FGMK"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Auth
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();

export default app;


