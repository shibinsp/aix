import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  BookOpen,
  Clock,
  Trophy,
  Filter,
  Search,
  Loader2,
  Trash2,
  X,
  AlertTriangle
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { coursesApi } from '@/services/api';

const DIFFICULTIES = ['beginner', 'intermediate', 'advanced', 'expert'];
const CATEGORIES = [
  { value: 'web_security', label: 'Web Security' },
  { value: 'network_security', label: 'Network Security' },
  { value: 'malware_analysis', label: 'Malware Analysis' },
  { value: 'cryptography', label: 'Cryptography' },
  { value: 'forensics', label: 'Forensics' },
  { value: 'cloud_security', label: 'Cloud Security' },
  { value: 'penetration_testing', label: 'Penetration Testing' },
];

export default function Courses() {
  const router = useRouter();
  const { isAuthenticated, hasHydrated } = useAuthStore();
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [difficulty, setDifficulty] = useState('');

  const { data: courses, isLoading } = useQuery({
    queryKey: ['courses', { search, category, difficulty }],
    queryFn: () => coursesApi.list({ search, category, difficulty }),
    enabled: isAuthenticated,
  });

  useEffect(() => {
    if (!hasHydrated) return;

    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [hasHydrated, isAuthenticated, router]);

  // Show loading until hydrated
  if (!hasHydrated) {
    return (
      <div className="p-8 flex justify-center items-center min-h-[400px]">
        <div className="w-8 h-8 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Courses</h1>
        <p className="text-gray-400">
          Structured learning paths to build your cybersecurity skills
        </p>
      </div>

      {/* Filters */}
      <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-4 mb-8">
        <div className="flex flex-wrap gap-4">
          {/* Search */}
          <div className="flex-1 min-w-64">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search courses..."
                className="w-full pl-10 pr-4 py-2 bg-cyber-darker border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent"
              />
            </div>
          </div>

          {/* Category Filter */}
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="px-4 py-2 bg-cyber-darker border border-gray-700 rounded-lg text-white focus:outline-none focus:border-cyber-accent"
          >
            <option value="">All Categories</option>
            {CATEGORIES.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label}
              </option>
            ))}
          </select>

          {/* Difficulty Filter */}
          <select
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value)}
            className="px-4 py-2 bg-cyber-darker border border-gray-700 rounded-lg text-white focus:outline-none focus:border-cyber-accent"
          >
            <option value="">All Levels</option>
            {DIFFICULTIES.map((diff) => (
              <option key={diff} value={diff}>
                {diff.charAt(0).toUpperCase() + diff.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Course Grid */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 text-cyber-accent animate-spin" />
        </div>
      ) : courses?.length > 0 ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {courses.map((course: any) => (
            <CourseCard key={course.id} course={course} />
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <BookOpen className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-xl font-medium text-white mb-2">No courses found</h3>
          <p className="text-gray-400">
            Try adjusting your filters or check back later for new content.
          </p>
        </div>
      )}
    </div>
  );
}

// Delete Confirmation Modal
function DeleteConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  courseName,
  isDeleting
}: {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  courseName: string;
  isDeleting: boolean;
}) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <div className="relative bg-cyber-dark border border-red-500/30 rounded-xl p-6 max-w-md w-full mx-4 shadow-2xl">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-white"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="p-3 bg-red-500/20 rounded-full">
            <AlertTriangle className="w-6 h-6 text-red-500" />
          </div>
          <h3 className="text-xl font-bold text-white">Delete Course</h3>
        </div>

        <p className="text-gray-300 mb-2">
          Are you sure you want to delete this course?
        </p>
        <p className="text-white font-medium mb-4 p-2 bg-cyber-darker rounded">
          "{courseName}"
        </p>
        <p className="text-gray-400 text-sm mb-6">
          This action cannot be undone. All modules and lessons will be permanently deleted.
        </p>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            disabled={isDeleting}
            className="flex-1 px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isDeleting}
            className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {isDeleting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Deleting...
              </>
            ) : (
              <>
                <Trash2 className="w-4 h-4" />
                Delete
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

function CourseCard({ course }: { course: any }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const difficultyColors: Record<string, string> = {
    beginner: 'bg-green-500/20 text-green-400',
    intermediate: 'bg-yellow-500/20 text-yellow-400',
    advanced: 'bg-orange-500/20 text-orange-400',
    expert: 'bg-red-500/20 text-red-400',
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await coursesApi.delete(course.id);
      // Invalidate and refetch courses list
      queryClient.invalidateQueries({ queryKey: ['courses'] });
      setShowDeleteModal(false);
    } catch (error) {
      console.error('Failed to delete course:', error);
      alert('Failed to delete course. Please try again.');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowDeleteModal(true);
  };

  return (
    <>
      <div
        onClick={() => router.push(`/courses/${course.id}`)}
        className="bg-cyber-dark rounded-xl border border-cyber-accent/20 overflow-hidden hover:border-cyber-accent/40 transition-colors cursor-pointer group relative"
      >
        {/* Delete Button */}
        <button
          onClick={handleDeleteClick}
          className="absolute top-3 right-3 z-10 p-2 bg-red-500/20 hover:bg-red-500/40 rounded-lg opacity-0 group-hover:opacity-100 transition-all duration-200"
          title="Delete course"
        >
          <Trash2 className="w-4 h-4 text-red-400" />
        </button>

        {/* Thumbnail */}
        <div className="h-40 bg-gradient-to-br from-cyber-accent/20 to-cyber-blue/20 flex items-center justify-center">
          <BookOpen className="w-16 h-16 text-cyber-accent/50 group-hover:text-cyber-accent transition-colors" />
        </div>

        {/* Content */}
        <div className="p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className={`text-xs px-2 py-1 rounded ${difficultyColors[course.difficulty] || difficultyColors.beginner}`}>
              {course.difficulty}
            </span>
            <span className="text-xs text-gray-500">
              {course.category?.replace(/_/g, ' ')}
            </span>
            {course.is_ai_generated && (
              <span className="text-xs px-2 py-1 rounded bg-purple-500/20 text-purple-400">
                AI Generated
              </span>
            )}
          </div>

          <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-cyber-accent transition-colors">
            {course.title}
          </h3>

          <p className="text-gray-400 text-sm mb-4 line-clamp-2">
            {course.short_description || course.description || 'No description available'}
          </p>

          <div className="flex items-center justify-between text-sm text-gray-500">
            <div className="flex items-center gap-1">
              <Clock className="w-4 h-4" />
              <span>{course.estimated_hours}h</span>
            </div>
            <div className="flex items-center gap-1">
              <Trophy className="w-4 h-4" />
              <span>{course.points} pts</span>
            </div>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleDelete}
        courseName={course.title}
        isDeleting={isDeleting}
      />
    </>
  );
}
