import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  BookOpen, ArrowLeft, Loader2, Search, Plus, X,
  GripVertical, Trash2, Save, CheckCircle, AlertCircle
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { batchesApi, coursesApi } from '@/services/api';
import AdminLayout from '@/components/common/AdminLayout';

interface Course {
  id: string;
  title: string;
  description?: string;
  difficulty_level: string;
  thumbnail_url?: string;
  lesson_count?: number;
  category?: string;
}

const difficultyColors: Record<string, string> = {
  beginner: 'bg-green-500/20 text-green-400',
  intermediate: 'bg-yellow-500/20 text-yellow-400',
  advanced: 'bg-red-500/20 text-red-400',
};

export default function BatchCurriculum() {
  const router = useRouter();
  const { batchId } = router.query;
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuthStore();
  const [assignedCourses, setAssignedCourses] = useState<string[]>([]);
  const [hasChanges, setHasChanges] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  const { data: batchData, isLoading: batchLoading } = useQuery({
    queryKey: ['batch', batchId],
    queryFn: () => batchesApi.get(batchId as string),
    enabled: isAuthenticated && !!batchId,
  });

  const { data: coursesData, isLoading: coursesLoading } = useQuery({
    queryKey: ['courses'],
    queryFn: () => coursesApi.list({ page_size: 100 }),
    enabled: isAuthenticated,
  });

  useEffect(() => {
    if (batchData) {
      const batch = batchData.batch || batchData;
      setAssignedCourses(batch.curriculum_courses || []);
    }
  }, [batchData]);

  const updateCurriculumMutation = useMutation({
    mutationFn: (courseIds: string[]) =>
      batchesApi.updateCurriculum(batchId as string, { course_ids: courseIds }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batch', batchId] });
      setHasChanges(false);
    },
  });

  if (!isAuthenticated) return null;

  const batch = batchData?.batch || batchData;
  const allCourses = coursesData?.items || coursesData || [];
  const assignedCourseDetails = assignedCourses
    .map(id => allCourses.find((c: Course) => c.id === id))
    .filter(Boolean) as Course[];
  const availableCourses = allCourses.filter(
    (c: Course) => !assignedCourses.includes(c.id)
  );

  const handleAddCourses = (courseIds: string[]) => {
    setAssignedCourses(prev => [...prev, ...courseIds]);
    setHasChanges(true);
    setShowAddModal(false);
  };

  const handleRemoveCourse = (courseId: string) => {
    setAssignedCourses(prev => prev.filter(id => id !== courseId));
    setHasChanges(true);
  };

  const handleReorder = (fromIndex: number, toIndex: number) => {
    const newOrder = [...assignedCourses];
    const [removed] = newOrder.splice(fromIndex, 1);
    newOrder.splice(toIndex, 0, removed);
    setAssignedCourses(newOrder);
    setHasChanges(true);
  };

  const handleSave = () => {
    updateCurriculumMutation.mutate(assignedCourses);
  };

  if (batchLoading || coursesLoading) {
    return (
      <div className="p-8 flex justify-center items-center min-h-[400px]">
        <Loader2 className="w-8 h-8 text-cyber-accent animate-spin" />
      </div>
    );
  }

  return (
    <AdminLayout title="Curriculum" subtitle={batch?.name}>
      {/* Header Actions */}
      <div className="flex justify-end gap-3 mb-8">
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 border border-purple-500/30 text-gray-300 rounded-lg hover:bg-purple-500/10 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Courses
        </button>
        <button
          onClick={handleSave}
          disabled={!hasChanges || updateCurriculumMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-500/90 transition-colors font-medium disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          {updateCurriculumMutation.isPending ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      {updateCurriculumMutation.isSuccess && (
        <div className="mb-6 p-4 bg-green-500/10 border border-green-500/30 rounded-lg flex items-center gap-3">
          <CheckCircle className="w-5 h-5 text-green-400" />
          <p className="text-green-400">Curriculum updated successfully!</p>
        </div>
      )}

      {updateCurriculumMutation.isError && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-400" />
          <p className="text-red-400">Failed to update curriculum. Please try again.</p>
        </div>
      )}

      {/* Assigned Courses */}
      <div className="bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-white">Assigned Courses</h2>
            <p className="text-sm text-gray-500">
              {assignedCourseDetails.length} course{assignedCourseDetails.length !== 1 ? 's' : ''} in curriculum
            </p>
          </div>
        </div>

        {assignedCourseDetails.length > 0 ? (
          <div className="space-y-3">
            {assignedCourseDetails.map((course, index) => (
              <CurriculumCourseCard
                key={course.id}
                course={course}
                index={index}
                total={assignedCourseDetails.length}
                onRemove={() => handleRemoveCourse(course.id)}
                onMoveUp={() => handleReorder(index, index - 1)}
                onMoveDown={() => handleReorder(index, index + 1)}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <BookOpen className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-xl font-medium text-white mb-2">No courses assigned</h3>
            <p className="text-gray-400 mb-4">Add courses to define the learning path for this batch.</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="px-4 py-2 bg-cyber-accent text-cyber-dark rounded-lg hover:bg-cyber-accent/90 transition-colors font-medium"
            >
              Add Courses
            </button>
          </div>
        )}
      </div>

      {/* Add Courses Modal */}
      {showAddModal && (
        <AddCoursesModal
          availableCourses={availableCourses}
          onClose={() => setShowAddModal(false)}
          onAdd={handleAddCourses}
        />
      )}
    </AdminLayout>
  );
}

function CurriculumCourseCard({
  course,
  index,
  total,
  onRemove,
  onMoveUp,
  onMoveDown,
}: {
  course: Course;
  index: number;
  total: number;
  onRemove: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
}) {
  return (
    <div className="flex items-center gap-4 p-4 bg-cyber-darker rounded-lg border border-cyber-accent/10 group hover:border-cyber-accent/30 transition-colors">
      <div className="flex flex-col gap-1">
        <button
          onClick={onMoveUp}
          disabled={index === 0}
          className="p-1 hover:bg-cyber-dark rounded disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
          </svg>
        </button>
        <button
          onClick={onMoveDown}
          disabled={index === total - 1}
          className="p-1 hover:bg-cyber-dark rounded disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      <div className="w-8 h-8 rounded-lg bg-cyber-accent/20 flex items-center justify-center text-cyber-accent font-bold">
        {index + 1}
      </div>

      {course.thumbnail_url ? (
        <img
          src={course.thumbnail_url}
          alt={course.title}
          className="w-16 h-12 rounded-lg object-cover"
        />
      ) : (
        <div className="w-16 h-12 rounded-lg bg-cyber-accent/10 flex items-center justify-center">
          <BookOpen className="w-6 h-6 text-cyber-accent/50" />
        </div>
      )}

      <div className="flex-1 min-w-0">
        <h3 className="text-white font-medium truncate">{course.title}</h3>
        <div className="flex items-center gap-2 mt-1">
          <span className={`text-xs px-2 py-0.5 rounded-full ${difficultyColors[course.difficulty_level] || 'bg-gray-500/20 text-gray-400'}`}>
            {course.difficulty_level}
          </span>
          {course.lesson_count && (
            <span className="text-xs text-gray-500">{course.lesson_count} lessons</span>
          )}
          {course.category && (
            <span className="text-xs text-gray-500">{course.category}</span>
          )}
        </div>
      </div>

      <button
        onClick={onRemove}
        className="p-2 hover:bg-red-500/10 rounded-lg transition-colors text-gray-400 hover:text-red-400 opacity-0 group-hover:opacity-100"
      >
        <Trash2 className="w-5 h-5" />
      </button>
    </div>
  );
}

function AddCoursesModal({
  availableCourses,
  onClose,
  onAdd,
}: {
  availableCourses: Course[];
  onClose: () => void;
  onAdd: (courseIds: string[]) => void;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [search, setSearch] = useState('');

  const filteredCourses = availableCourses.filter(course =>
    course.title.toLowerCase().includes(search.toLowerCase()) ||
    course.description?.toLowerCase().includes(search.toLowerCase()) ||
    course.category?.toLowerCase().includes(search.toLowerCase())
  );

  const toggleCourse = (courseId: string) => {
    setSelected(prev =>
      prev.includes(courseId)
        ? prev.filter(id => id !== courseId)
        : [...prev, courseId]
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-cyber-dark rounded-2xl border border-cyber-accent/30 p-6 max-w-2xl w-full mx-4 shadow-xl max-h-[80vh] overflow-hidden flex flex-col">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-white">Add Courses to Curriculum</h2>
          <button onClick={onClose} className="p-1 hover:bg-cyber-darker rounded-lg">
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search courses..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-cyber-darker border border-cyber-accent/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyber-accent/50"
          />
        </div>

        <div className="flex-1 overflow-y-auto mb-4">
          {filteredCourses.length > 0 ? (
            <div className="grid gap-3">
              {filteredCourses.map(course => (
                <label
                  key={course.id}
                  className={`flex items-center gap-4 p-4 rounded-lg border cursor-pointer transition-colors ${
                    selected.includes(course.id)
                      ? 'border-cyber-accent bg-cyber-accent/10'
                      : 'border-cyber-accent/20 hover:border-cyber-accent/40'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selected.includes(course.id)}
                    onChange={() => toggleCourse(course.id)}
                    className="sr-only"
                  />
                  <div className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 ${
                    selected.includes(course.id)
                      ? 'border-cyber-accent bg-cyber-accent'
                      : 'border-gray-500'
                  }`}>
                    {selected.includes(course.id) && (
                      <svg className="w-3 h-3 text-cyber-dark" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    )}
                  </div>

                  {course.thumbnail_url ? (
                    <img
                      src={course.thumbnail_url}
                      alt={course.title}
                      className="w-16 h-12 rounded-lg object-cover flex-shrink-0"
                    />
                  ) : (
                    <div className="w-16 h-12 rounded-lg bg-cyber-accent/10 flex items-center justify-center flex-shrink-0">
                      <BookOpen className="w-6 h-6 text-cyber-accent/50" />
                    </div>
                  )}

                  <div className="flex-1 min-w-0">
                    <h3 className="text-white font-medium truncate">{course.title}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${difficultyColors[course.difficulty_level] || 'bg-gray-500/20 text-gray-400'}`}>
                        {course.difficulty_level}
                      </span>
                      {course.category && (
                        <span className="text-xs text-gray-500">{course.category}</span>
                      )}
                    </div>
                  </div>
                </label>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <BookOpen className="w-12 h-12 text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500">
                {availableCourses.length === 0
                  ? 'All courses have been assigned'
                  : 'No courses match your search'}
              </p>
            </div>
          )}
        </div>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-cyber-accent/30 text-gray-300 rounded-lg hover:bg-cyber-darker transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onAdd(selected)}
            disabled={selected.length === 0}
            className="flex-1 px-4 py-2 bg-cyber-accent text-cyber-dark rounded-lg hover:bg-cyber-accent/90 transition-colors font-medium disabled:opacity-50"
          >
            Add {selected.length} Course{selected.length !== 1 ? 's' : ''}
          </button>
        </div>
      </div>
    </div>
  );
}
