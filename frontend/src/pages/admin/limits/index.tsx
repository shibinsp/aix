import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Gauge, Loader2, Save, RotateCcw, AlertCircle, CheckCircle,
  BookOpen, Beaker, Terminal, Monitor, HardDrive, Shield
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { limitsApi } from '@/services/api';
import AdminLayout from '@/components/common/AdminLayout';

interface SystemLimits {
  max_courses_per_user: number;
  max_ai_generated_courses: number;
  max_concurrent_labs: number;
  max_lab_duration_minutes: number;
  max_terminal_hours_monthly: number;
  max_desktop_hours_monthly: number;
  enable_persistent_vm: boolean;
  max_storage_gb: number;
}

const defaultLimits: SystemLimits = {
  max_courses_per_user: 5,
  max_ai_generated_courses: 3,
  max_concurrent_labs: 1,
  max_lab_duration_minutes: 60,
  max_terminal_hours_monthly: 30,
  max_desktop_hours_monthly: 10,
  enable_persistent_vm: true,
  max_storage_gb: 2,
};

export default function SystemLimitsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isAuthenticated, user } = useAuthStore();
  const [limits, setLimits] = useState<SystemLimits>(defaultLimits);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  const { data: limitsData, isLoading } = useQuery({
    queryKey: ['system-limits'],
    queryFn: () => limitsApi.getDefaults(),
    enabled: isAuthenticated,
  });

  useEffect(() => {
    if (limitsData) {
      setLimits(limitsData);
    }
  }, [limitsData]);

  const updateMutation = useMutation({
    mutationFn: (data: SystemLimits) => limitsApi.updateDefaults(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-limits'] });
      setHasChanges(false);
    },
  });

  const handleChange = (key: keyof SystemLimits, value: number | boolean) => {
    setLimits(prev => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  const handleReset = () => {
    setLimits(defaultLimits);
    setHasChanges(true);
  };

  const handleSave = () => {
    updateMutation.mutate(limits);
  };

  if (!isAuthenticated) return null;

  if (isLoading) {
    return (
      <div className="p-8 flex justify-center items-center min-h-[400px]">
        <Loader2 className="w-8 h-8 text-cyber-accent animate-spin" />
      </div>
    );
  }

  return (
    <AdminLayout title="System Resource Limits" subtitle="Configure default limits for all organizations and users">
      {/* Header Actions */}
      <div className="flex items-center gap-4 mb-8">
        <div className="flex-1" />  {/* Spacer since title is in AdminLayout */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-4 py-2 border border-cyber-accent/30 text-gray-300 rounded-lg hover:bg-cyber-dark transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Reset to Defaults
          </button>
          <button
            onClick={handleSave}
            disabled={!hasChanges || updateMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-cyber-accent text-cyber-dark rounded-lg hover:bg-cyber-accent/90 transition-colors font-medium disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {updateMutation.isSuccess && (
        <div className="mb-6 p-4 bg-green-500/10 border border-green-500/30 rounded-lg flex items-center gap-3">
          <CheckCircle className="w-5 h-5 text-green-400" />
          <p className="text-green-400">System limits updated successfully!</p>
        </div>
      )}

      {updateMutation.isError && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-400" />
          <p className="text-red-400">Failed to save limits. Please try again.</p>
        </div>
      )}

      {/* Info Banner */}
      <div className="mb-6 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg flex items-start gap-3">
        <Shield className="w-5 h-5 text-blue-400 mt-0.5" />
        <div>
          <p className="text-blue-400 font-medium">System-wide defaults</p>
          <p className="text-sm text-blue-400/70">
            These limits apply to all organizations by default. Individual organizations can have their own limits configured which will override these defaults.
          </p>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Courses Section */}
        <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Course Limits</h2>
              <p className="text-sm text-gray-500">Control course creation and access</p>
            </div>
          </div>

          <div className="space-y-5">
            <LimitSlider
              label="Max Courses per User"
              description="Total number of courses a user can create (lifetime)"
              value={limits.max_courses_per_user}
              min={1}
              max={100}
              onChange={(v) => handleChange('max_courses_per_user', v)}
            />
            <LimitSlider
              label="Max AI-Generated Courses"
              description="AI course generations per month"
              value={limits.max_ai_generated_courses}
              min={0}
              max={50}
              onChange={(v) => handleChange('max_ai_generated_courses', v)}
            />
          </div>
        </div>

        {/* Labs Section */}
        <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
              <Beaker className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Lab Limits</h2>
              <p className="text-sm text-gray-500">Control lab sessions and duration</p>
            </div>
          </div>

          <div className="space-y-5">
            <LimitSlider
              label="Max Concurrent Labs"
              description="Simultaneous active lab sessions"
              value={limits.max_concurrent_labs}
              min={1}
              max={10}
              onChange={(v) => handleChange('max_concurrent_labs', v)}
            />
            <LimitSlider
              label="Max Lab Duration"
              description="Maximum minutes per lab session"
              value={limits.max_lab_duration_minutes}
              min={15}
              max={480}
              step={15}
              suffix=" min"
              onChange={(v) => handleChange('max_lab_duration_minutes', v)}
            />
          </div>
        </div>

        {/* Terminal Section */}
        <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
              <Terminal className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Terminal Access</h2>
              <p className="text-sm text-gray-500">Control persistent terminal usage</p>
            </div>
          </div>

          <div className="space-y-5">
            <LimitSlider
              label="Monthly Terminal Hours"
              description="Hours of terminal access per month"
              value={limits.max_terminal_hours_monthly}
              min={1}
              max={500}
              suffix=" hrs"
              onChange={(v) => handleChange('max_terminal_hours_monthly', v)}
            />
          </div>
        </div>

        {/* Desktop Section */}
        <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-lg bg-orange-500/20 flex items-center justify-center">
              <Monitor className="w-5 h-5 text-orange-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Desktop Access</h2>
              <p className="text-sm text-gray-500">Control virtual desktop usage</p>
            </div>
          </div>

          <div className="space-y-5">
            <LimitSlider
              label="Monthly Desktop Hours"
              description="Hours of desktop access per month"
              value={limits.max_desktop_hours_monthly}
              min={1}
              max={200}
              suffix=" hrs"
              onChange={(v) => handleChange('max_desktop_hours_monthly', v)}
            />
          </div>
        </div>

        {/* Storage Section */}
        <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6 lg:col-span-2">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-lg bg-cyan-500/20 flex items-center justify-center">
              <HardDrive className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Storage & Persistence</h2>
              <p className="text-sm text-gray-500">Control data persistence and storage</p>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <LimitSlider
              label="Max Storage"
              description="Persistent storage per user"
              value={limits.max_storage_gb}
              min={1}
              max={100}
              suffix=" GB"
              onChange={(v) => handleChange('max_storage_gb', v)}
            />

            <div>
              <div className="flex items-center justify-between mb-2">
                <div>
                  <p className="text-white font-medium">Enable Persistent VM</p>
                  <p className="text-sm text-gray-500">Allow users to keep their environment data</p>
                </div>
                <button
                  onClick={() => handleChange('enable_persistent_vm', !limits.enable_persistent_vm)}
                  className={`relative w-12 h-6 rounded-full transition-colors ${
                    limits.enable_persistent_vm ? 'bg-cyber-accent' : 'bg-gray-600'
                  }`}
                >
                  <div
                    className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                      limits.enable_persistent_vm ? 'left-7' : 'left-1'
                    }`}
                  />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}

function LimitSlider({
  label,
  description,
  value,
  min,
  max,
  step = 1,
  suffix = '',
  onChange,
}: {
  label: string;
  description: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  suffix?: string;
  onChange: (value: number) => void;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <div>
          <p className="text-white font-medium">{label}</p>
          <p className="text-sm text-gray-500">{description}</p>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="number"
            value={value}
            min={min}
            max={max}
            step={step}
            onChange={(e) => onChange(Math.min(max, Math.max(min, parseInt(e.target.value) || min)))}
            className="w-20 px-2 py-1 bg-cyber-darker border border-cyber-accent/20 rounded text-white text-center text-sm focus:outline-none focus:border-cyber-accent/50"
          />
          <span className="text-gray-500 text-sm">{suffix}</span>
        </div>
      </div>
      <input
        type="range"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(parseInt(e.target.value))}
        className="w-full h-2 bg-cyber-darker rounded-lg appearance-none cursor-pointer accent-cyber-accent"
      />
      <div className="flex justify-between text-xs text-gray-500 mt-1">
        <span>{min}{suffix}</span>
        <span>{max}{suffix}</span>
      </div>
    </div>
  );
}
