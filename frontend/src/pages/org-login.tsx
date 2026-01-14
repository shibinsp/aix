import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { Shield, AlertCircle } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { authApi } from '@/services/api';

export default function OrgLogin() {
  const router = useRouter();
  const { setAuth } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const data = await authApi.login(email, password);

      // Check if user has org admin access
      const orgRole = data.user.org_role?.toLowerCase();
      const isOrgAdmin = orgRole && ['owner', 'admin', 'instructor'].includes(orgRole);
      const hasOrg = data.user.organization_id;

      if (!isOrgAdmin || !hasOrg) {
        setError('You do not have organization management permissions. Please contact your administrator.');
        setLoading(false);
        return;
      }

      setAuth(data.user, data.access_token);
      router.push(`/portal/${data.user.organization_id}`);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else if (Array.isArray(detail) && detail.length > 0) {
        setError(detail[0]?.msg || 'Validation error');
      } else {
        setError('Login failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-cyber-darker p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-3">
            <Shield className="w-12 h-12 text-cyber-accent" />
            <span className="text-3xl font-bold text-white">
              Cyber<span className="text-cyber-accent">AIx</span>
            </span>
          </Link>
          <p className="text-gray-400 mt-2">Organization Portal Login</p>
        </div>

        <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <span className="text-sm">{error}</span>
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
                Email or Username
              </label>
              <input
                type="text"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 bg-cyber-darker border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent transition-colors"
                placeholder="admin@organization.com"
                required
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
                Password
              </label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 bg-cyber-darker border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent transition-colors"
                placeholder="Enter your password"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-cyber-accent text-cyber-dark font-semibold rounded-lg hover:bg-cyber-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <div className="w-5 h-5 loading-spinner" />
                  Signing in...
                </span>
              ) : (
                'Sign In to Portal'
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-gray-400">
              Not an organization admin?{' '}
              <Link href="/login" className="text-cyber-accent hover:underline">
                Regular Login
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
