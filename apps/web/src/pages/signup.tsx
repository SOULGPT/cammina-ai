import { useState } from "react";
import { supabase } from "../lib/supabase";
import { useNavigate, Link } from "react-router-dom";
export default function SignUp() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const handleSignUp = async () => {
    setError("");
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    setLoading(true);
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) {
      setError(error.message);
    } else {
      setSuccess(true);
    }
    setLoading(false);
  };
  return (
    <div style={{ background: "#0f0f0f", minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ background: "#1a1a1a", padding: "40px", borderRadius: "12px", width: "400px", border: "1px solid #2d2d2d" }}>
        <h1 style={{ color: "white", textAlign: "center", marginBottom: "8px" }}>Create your account</h1>
        <p style={{ color: "#888", textAlign: "center", marginBottom: "32px" }}>Join Cammina AI</p>
        {success ? (
          <div style={{ color: "#7c3aed", textAlign: "center", padding: "20px" }}>
            Check your email to confirm your account!
          </div>
        ) : (
          <>
            {error && <p style={{ color: "#ef4444", marginBottom: "16px", fontSize: "14px" }}>{error}</p>}
            <input type="email" placeholder="[you@example.com](mailto:you@example.com)" value={email} onChange={e => setEmail([e.target](http://e.target).value)}
              style={{ width: "100%", padding: "12px", background: "#0f0f0f", border: "1px solid #2d2d2d", borderRadius: "8px", color: "white", marginBottom: "16px", boxSizing: "border-box" }} />
            <input type="password" placeholder="Password" value={password} onChange={e => setPassword([e.target](http://e.target).value)}
              style={{ width: "100%", padding: "12px", background: "#0f0f0f", border: "1px solid #2d2d2d", borderRadius: "8px", color: "white", marginBottom: "16px", boxSizing: "border-box" }} />
            <input type="password" placeholder="Confirm Password" value={confirm} onChange={e => setConfirm([e.target](http://e.target).value)}
              style={{ width: "100%", padding: "12px", background: "#0f0f0f", border: "1px solid #2d2d2d", borderRadius: "8px", color: "white", marginBottom: "24px", boxSizing: "border-box" }} />
            <button onClick={handleSignUp} disabled={loading}
              style={{ width: "100%", padding: "12px", background: "#7c3aed", border: "none", borderRadius: "8px", color: "white", fontSize: "16px", cursor: "pointer", marginBottom: "16px" }}>
              {loading ? "Creating account..." : "Sign Up"}
            </button>
            <p style={{ color: "#888", textAlign: "center", fontSize: "14px" }}>
              Already have an account?{" "}
              <Link to="/login" style={{ color: "#7c3aed" }}>Sign in</Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
