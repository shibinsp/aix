import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import {
  BookOpen,
  ArrowLeft,
  Plus,
  X,
  Check,
  GripVertical,
  Trash2,
  Clock,
  Users
} from 'lucide-react';
import PortalLayout from '@/components/common/PortalLayout';
import { api } from '@/services/api';

interface Course {
  id: string;
  title: string;
  description: string;
  difficulty: string;
  duration_hours: number;
  enrolled_count?: number;
}

interface CurriculumCourse extends Course {
  order: number;
  required: boolean;
}

export default function BatchCurriculum() {
  const router = useRouter();
  const { orgId, batchId } = router.query;
  const [curriculum, setCurriculum] = useState<CurriculumCourse[]>([]);
  const [availableCourses, setAvailableCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedCourses, setSelectedCourses] = useState<string[]>([]);

  useEffect(() => {
    if (orgId && batchId) {
      fetchCurriculum();
    }
  }, [orgId, batchId]);

  const fetchCurriculum = async () => {
    try {
      const res = await api.get(`/organizations/${orgId}/batches/${batchId}/curriculum`);
      setCurriculum(res.data);
    } catch (error) {
      setCurriculum([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableCourses = async () => {
    try {
      const res = await api.get('/courses');
      const curriculumIds = curriculum.map(c => c.id);
      setAvailableCourses(res.data.filter((c: Course) => !curriculumIds.includes(c.id)));
    } catch (error) {
      setAvailableCourses([]);
    }
  };

  const handleAddCourses = async () => {
    try {
      await api.post(`/organizations/${orgId}/batches/${batchId}/curriculum`, {
        course_ids: selectedCourses
      });
      setShowAddModal(false);
      setSelectedCourses([]);
      fetchCurriculum();
    } catch (error) {
      console.error('Failed to add courses:', error);
    }
  };

  const handleRemoveCourse = async (courseId: string) => {
    try {
      await api.delete(`/organizations/${orgId}/batches/${batchId}/curriculum/${courseId}`);
      fetchCurriculum();
    } catch (error) {
      console.error('Failed to remove course:', error);
    }
  };

  const getDifficultyColor = (difficulty: string) => {
    const colors: Record<string, string> = {
      beginner: 'bg-cyber-accent/20 text-cyber-accent',
      intermediate: 'bg-yellow-500/20 text-yellow-400',
      advanced: 'bg-red-500/20 text-red-400'
    };
    return colors[difficulty.toLowerCase()] || colors.beginner;
  };

  return (
    <PortalLayout>
      <Link
        href={`/portal/${orgId}/batches/${batchId}`}
        className="inline-flex items-center gap-2 text-gray-400 hover:text-white mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Batch
      </Link>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Curriculum</h1>
          <p className="text-gray-400 mt-1">Manage courses assigned to this batch</p>
        </div>
        <button
          onClick={() => {
            fetchAvailableCourses();
            setShowAddModal(true);
          }}
          className="flex items-center gap-2 px-4 py-2.5 bg-cyber-accent text-cyber-dark font-semibold rounded-lg hover:bg-cyber-accent/90 transition-colors"
        >
          <Plus className="w-5 h-5" />
          Add Courses
        </button>
      </div>

      {/* Curriculum List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-cyber-accent/30 border-t-cyber-accent rounded-full animate-spin" />
        </div>
      ) : curriculum.length === 0 ? (
        <div className="text-center py-12 bg-cyber-dark rounded-xl border border-cyber-accent/20">
          <BookOpen className="w-12 h-12 text-gray-600 mx-auto mb-3" />
          <p className="text-gray-400">No courses in curriculum</p>
          <p className="text-sm text-gray-500 mt-1">Add courses to create a learning path for this batch</p>
          <button
            onClick={() => {
              fetchAvailableCourses();
              setShowAddModal(true);
            }}
            className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-cyber-accent/10 text-cyber-accent rounded-lg hover:bg-cyber-accent/20 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Courses
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {curriculum.map((course, index) => (
            <div
              key={course.id}
              className="flex items-center gap-4 p-4 bg-cyber-dark rounded-xl border border-cyber-accent/20 hover:border-cyber-accent/40 transition-all"
            >
              <div className="flex items-center gap-2 text-gray-500">
                <GripVertical className="w-5 h-5 cursor-grab" />
                <span className="w-6 h-6 rounded-full bg-cyber-accent/20 flex items-center justify-center text-cyber-accent text-sm font-medium">
                  {index + 1}
                </span>
              </div>

              <div className="flex-1">
                <div className="flex items-center gap-3 mb-1">
                  <h3 className="text-white font-medium">{course.title}</h3>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${getDifficultyColor(course.difficulty)}`}>
                    {course.difficulty}
                  </span>
                  {course.required && (
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-purple-500/20 text-purple-400">
                      Required
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-500 line-clamp-1">{course.description}</p>
              </div>

              <div className="flex items-center gap-4 text-sm text-gray-500">
                <div className="flex items-center gap-1.5">
                  <Clock className="w-4 h-4" />
                  <span>{course.duration_hours}h</span>
                </div>
                {course.enrolled_count !== undefined && (
                  <div className="flex items-center gap-1.5">
                    <Users className="w-4 h-4" />
                    <span>{course.enrolled_count}</span>
                  </div>
                )}
              </div>

              <button
                onClick={() => handleRemoveCourse(course.id)}
                className="p-2 text-gray-400 hover:text-red-400 rounded-lg hover:bg-white/5 transition-colors"
              >
                <Trash2 className="w-5 h-5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Summary */}
      {curriculum.length > 0 && (
        <div className="mt-6 p-4 bg-cyber-dark rounded-xl border border-cyber-accent/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6 text-sm">
              <div>
                <span className="text-gray-500">Total Courses:</span>
                <span className="ml-2 text-white font-medium">{curriculum.length}</span>
              </div>
              <div>
                <span className="text-gray-500">Total Duration:</span>
                <span className="ml-2 text-white font-medium">
                  {curriculum.reduce((sum, c) => sum + c.duration_hours, 0)} hours
                </span>
              </div>
              <div>
                <span className="text-gray-500">Required:</span>
                <span className="ml-2 text-white font-medium">
                  {curriculum.filter(c => c.required).length}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add Courses Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="w-full max-w-lg bg-cyber-dark rounded-xl border border-cyber-accent/20 p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-white">Add Courses to Curriculum</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-white/5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="max-h-80 overflow-y-auto space-y-2">
              {availableCourses.length === 0 ? (
                <p className="text-center text-gray-400 py-4">No available courses to add</p>
              ) : (
                availableCourses.map((course) => (
                  <button
                    key={course.id}
                    onClick={() => {
                      setSelectedCourses(prev =>
                        prev.includes(course.id)
                          ? prev.filter(id => id !== course.id)
                          : [...prev, course.id]
                      );
                    }}
                    className={`w-full flex items-center justify-between p-4 rounded-lg border transition-colors text-left ${
                      selectedCourses.includes(course.id)
                        ? 'border-[#00ff9d] bg-cyber-accent/10'
                        : 'border-cyber-accent/20 hover:border-cyber-accent/40'
                    }`}
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="text-white font-medium">{course.title}</p>
                        <span className={`px-2 py-0.5 rounded text-xs ${getDifficultyColor(course.difficulty)}`}>
                          {course.difficulty}
                        </span>
                      </div>
                      <p className="text-sm text-gray-500 line-clamp-1">{course.description}</p>
                    </div>
                    {selectedCourses.includes(course.id) && (
                      <Check className="w-5 h-5 text-cyber-accent ml-4" />
                    )}
                  </button>
                ))
              )}
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowAddModal(false)}
                className="flex-1 px-4 py-2.5 border border-cyber-accent/20 text-gray-400 rounded-lg hover:bg-white/5 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAddCourses}
                disabled={selectedCourses.length === 0}
                className="flex-1 px-4 py-2.5 bg-cyber-accent text-cyber-dark font-semibold rounded-lg hover:bg-cyber-accent/90 transition-colors disabled:opacity-50"
              >
                Add {selectedCourses.length > 0 && `(${selectedCourses.length})`}
              </button>
            </div>
          </div>
        </div>
      )}
    </PortalLayout>
  );
}
