import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import {
  Settings,
  Building2,
  Bell,
  Shield,
  Save,
  AlertCircle,
  CheckCircle
} from 'lucide-react';
import PortalLayout from '@/components/common/PortalLayout';
import { useAuthStore } from '@/store/authStore';
import { organizationsApi } from '@/services/api';

interface OrgSettings {
  name: string;
  description: string;
  website: string;
  contact_email: string;
  notifications: {
    member_joined: boolean;
    course_completed: boolean;
    weekly_digest: boolean;
    batch_alerts: boolean;
  };
  defaults: {
    default_role: string;
    auto_enroll_courses: boolean;
    require_approval: boolean;
  };
}

export default function PortalSettings() {
  const router = useRouter();
  const { orgId } = router.query;
  const { user } = useAuthStore();
  const [settings, setSettings] = useState<OrgSettings>({
    name: '',
    description: '',
    website: '',
    contact_email: '',
    notifications: {
      member_joined: true,
      course_completed: true,
      weekly_digest: true,
      batch_alerts: true
    },
    defaults: {
      default_role: 'member',
      auto_enroll_courses: false,
      require_approval: false
    }
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const isOwner = user?.org_role?.toLowerCase() === 'owner';

  useEffect(() => {
    if (orgId) {
      fetchSettings();
    }
  }, [orgId]);

  const fetchSettings = async () => {
    if (typeof orgId !== 'string') return;

    try {
      const orgData = await organizationsApi.get(orgId);
      setSettings({
        name: orgData.name || '',
        description: orgData.description || '',
        website: orgData.website || '',
        contact_email: orgData.contact_email || '',
        notifications: settings.notifications,
        defaults: settings.defaults
      });
    } catch (error) {
      // Keep defaults
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (typeof orgId !== 'string') return;

    setSaving(true);
    setMessage(null);
    try {
      await organizationsApi.update(orgId, {
        name: settings.name,
        description: settings.description,
        contact_email: settings.contact_email
      });
      setMessage({ type: 'success', text: 'Settings saved successfully!' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to save settings. Please try again.' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <PortalLayout title="Settings" subtitle="Manage organization settings">
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="max-w-3xl space-y-8">
          {/* Message */}
          {message && (
            <div className={`flex items-center gap-2 p-4 rounded-lg ${
              message.type === 'success'
                ? 'bg-cyber-accent/10 border border-cyber-accent/20 text-cyber-accent'
                : 'bg-red-500/10 border border-red-500/20 text-red-400'
            }`}>
              {message.type === 'success' ? (
                <CheckCircle className="w-5 h-5" />
              ) : (
                <AlertCircle className="w-5 h-5" />
              )}
              <span>{message.text}</span>
            </div>
          )}

          {/* Organization Info */}
          <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 rounded-lg bg-cyber-accent/10">
                <Building2 className="w-5 h-5 text-cyber-accent" />
              </div>
              <h2 className="text-lg font-semibold text-white">Organization Information</h2>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Organization Name
                </label>
                <input
                  type="text"
                  value={settings.name}
                  onChange={(e) => setSettings({ ...settings, name: e.target.value })}
                  disabled={!isOwner}
                  className="w-full px-4 py-2.5 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent disabled:opacity-50 disabled:cursor-not-allowed"
                  placeholder="Your organization name"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Description
                </label>
                <textarea
                  value={settings.description}
                  onChange={(e) => setSettings({ ...settings, description: e.target.value })}
                  disabled={!isOwner}
                  className="w-full px-4 py-2.5 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent resize-none disabled:opacity-50 disabled:cursor-not-allowed"
                  rows={3}
                  placeholder="Brief description of your organization"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Website
                  </label>
                  <input
                    type="url"
                    value={settings.website}
                    onChange={(e) => setSettings({ ...settings, website: e.target.value })}
                    disabled={!isOwner}
                    className="w-full px-4 py-2.5 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent disabled:opacity-50 disabled:cursor-not-allowed"
                    placeholder="https://yourwebsite.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Contact Email
                  </label>
                  <input
                    type="email"
                    value={settings.contact_email}
                    onChange={(e) => setSettings({ ...settings, contact_email: e.target.value })}
                    disabled={!isOwner}
                    className="w-full px-4 py-2.5 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent disabled:opacity-50 disabled:cursor-not-allowed"
                    placeholder="contact@organization.com"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Notifications */}
          <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 rounded-lg bg-blue-500/10">
                <Bell className="w-5 h-5 text-blue-400" />
              </div>
              <h2 className="text-lg font-semibold text-white">Notifications</h2>
            </div>

            <div className="space-y-4">
              {[
                { key: 'member_joined', label: 'New member joined', description: 'Get notified when someone joins your organization' },
                { key: 'course_completed', label: 'Course completion', description: 'Get notified when members complete courses' },
                { key: 'weekly_digest', label: 'Weekly digest', description: 'Receive a weekly summary of organization activity' },
                { key: 'batch_alerts', label: 'Batch alerts', description: 'Get alerts about batch deadlines and milestones' }
              ].map((item) => (
                <label
                  key={item.key}
                  className="flex items-center justify-between p-4 rounded-lg bg-cyber-darker border border-cyber-accent/10 cursor-pointer hover:border-cyber-accent/30 transition-colors"
                >
                  <div>
                    <p className="text-white font-medium">{item.label}</p>
                    <p className="text-sm text-gray-500">{item.description}</p>
                  </div>
                  <div className="relative">
                    <input
                      type="checkbox"
                      checked={settings.notifications[item.key as keyof typeof settings.notifications]}
                      onChange={(e) => setSettings({
                        ...settings,
                        notifications: {
                          ...settings.notifications,
                          [item.key]: e.target.checked
                        }
                      })}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-700 rounded-full peer peer-checked:bg-cyber-accent transition-colors" />
                    <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Default Settings */}
          <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 rounded-lg bg-purple-500/10">
                <Shield className="w-5 h-5 text-purple-400" />
              </div>
              <h2 className="text-lg font-semibold text-white">Default Settings</h2>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Default Role for New Members
                </label>
                <select
                  value={settings.defaults.default_role}
                  onChange={(e) => setSettings({
                    ...settings,
                    defaults: { ...settings.defaults, default_role: e.target.value }
                  })}
                  disabled={!isOwner}
                  className="w-full px-4 py-2.5 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white focus:outline-none focus:border-cyber-accent disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <option value="member">Member</option>
                  <option value="instructor">Instructor</option>
                </select>
              </div>

              <label className="flex items-center justify-between p-4 rounded-lg bg-cyber-darker border border-cyber-accent/10 cursor-pointer hover:border-cyber-accent/30 transition-colors">
                <div>
                  <p className="text-white font-medium">Auto-enroll in courses</p>
                  <p className="text-sm text-gray-500">Automatically enroll new members in default courses</p>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={settings.defaults.auto_enroll_courses}
                    onChange={(e) => setSettings({
                      ...settings,
                      defaults: { ...settings.defaults, auto_enroll_courses: e.target.checked }
                    })}
                    disabled={!isOwner}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-700 rounded-full peer peer-checked:bg-cyber-accent transition-colors peer-disabled:opacity-50" />
                  <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
                </div>
              </label>

              <label className="flex items-center justify-between p-4 rounded-lg bg-cyber-darker border border-cyber-accent/10 cursor-pointer hover:border-cyber-accent/30 transition-colors">
                <div>
                  <p className="text-white font-medium">Require approval for new members</p>
                  <p className="text-sm text-gray-500">Members need admin approval to join the organization</p>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={settings.defaults.require_approval}
                    onChange={(e) => setSettings({
                      ...settings,
                      defaults: { ...settings.defaults, require_approval: e.target.checked }
                    })}
                    disabled={!isOwner}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-700 rounded-full peer peer-checked:bg-cyber-accent transition-colors peer-disabled:opacity-50" />
                  <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
                </div>
              </label>
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-end">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 px-6 py-3 bg-cyber-accent text-cyber-dark font-semibold rounded-lg hover:bg-cyber-accent/90 transition-colors disabled:opacity-50"
            >
              {saving ? (
                <>
                  <div className="w-5 h-5 border-2 border-[#0a1510]/30 border-t-[#0a1510] rounded-full animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-5 h-5" />
                  Save Settings
                </>
              )}
            </button>
          </div>

          {/* Non-owner notice */}
          {!isOwner && (
            <div className="flex items-center gap-2 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg text-yellow-400 text-sm">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span>Only organization owners can modify these settings.</span>
            </div>
          )}
        </div>
      )}
    </PortalLayout>
  );
}
