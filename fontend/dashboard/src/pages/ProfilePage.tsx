/**
 * Profile Page
 * User profile management interface
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../shared/AuthContext';

interface Profile {
  id: string;
  user_id: string;
  display_name: string;
  first_name: string;
  last_name: string;
  email: string;
  bio: string;
  title: string;
  company: string;
  location: string;
  phone: string;
  website: string;
  twitter: string;
  linkedin: string;
  github: string;
}

export const ProfilePage: React.FC = () => {
  const { user } = useAuth();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [formData, setFormData] = useState({
    display_name: '',
    first_name: '',
    last_name: '',
    bio: '',
    title: '',
    company: '',
    location: '',
    phone: '',
    website: '',
    twitter: '',
    linkedin: '',
    github: '',
  });

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const response = await fetch('/api/accounts/profile/', {
        credentials: 'include',
      });
      const data = await response.json();

      if (data.success && data.profile) {
        setProfile(data.profile);
        setFormData({
          display_name: data.profile.display_name || '',
          first_name: data.profile.first_name || '',
          last_name: data.profile.last_name || '',
          bio: data.profile.bio || '',
          title: data.profile.title || '',
          company: data.profile.company || '',
          location: data.profile.location || '',
          phone: data.profile.phone || '',
          website: data.profile.website || '',
          twitter: data.profile.twitter || '',
          linkedin: data.profile.linkedin || '',
          github: data.profile.github || '',
        });
      }
    } catch (err) {
      console.error('Failed to load profile:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setIsSaving(true);

    try {
      const response = await fetch('/api/accounts/profile/update/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (data.success) {
        setProfile(data.profile);
        setSuccess('Profile updated successfully!');
        setIsEditing(false);
      } else {
        setError(data.error || 'Failed to update profile');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to update profile');
    } finally {
      setIsSaving(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  if (isLoading) {
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '400px' }}>
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="container py-4">
      <div className="row">
        <div className="col-md-8 mx-auto">
          <div className="card shadow-sm">
            <div className="card-body">
              <div className="d-flex justify-content-between align-items-center mb-4">
                <h2 className="mb-0">Profile</h2>
                {!isEditing && (
                  <button
                    className="btn btn-primary"
                    onClick={() => setIsEditing(true)}
                  >
                    Edit Profile
                  </button>
                )}
              </div>

              {error && (
                <div className="alert alert-danger" role="alert">
                  {error}
                </div>
              )}

              {success && (
                <div className="alert alert-success" role="alert">
                  {success}
                </div>
              )}

              <form onSubmit={handleSubmit}>
                <div className="mb-3">
                  <label className="form-label fw-bold">Email</label>
                  <input
                    type="text"
                    className="form-control"
                    value={user?.email || ''}
                    disabled
                  />
                  <div className="form-text">Email cannot be changed</div>
                </div>

                <div className="row mb-3">
                  <div className="col-md-6">
                    <label htmlFor="first_name" className="form-label">
                      First Name
                    </label>
                    <input
                      type="text"
                      className="form-control"
                      id="first_name"
                      name="first_name"
                      value={formData.first_name}
                      onChange={handleChange}
                      disabled={!isEditing}
                    />
                  </div>
                  <div className="col-md-6">
                    <label htmlFor="last_name" className="form-label">
                      Last Name
                    </label>
                    <input
                      type="text"
                      className="form-control"
                      id="last_name"
                      name="last_name"
                      value={formData.last_name}
                      onChange={handleChange}
                      disabled={!isEditing}
                    />
                  </div>
                </div>

                <div className="mb-3">
                  <label htmlFor="display_name" className="form-label">
                    Display Name
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="display_name"
                    name="display_name"
                    value={formData.display_name}
                    onChange={handleChange}
                    disabled={!isEditing}
                  />
                </div>

                <div className="mb-3">
                  <label htmlFor="bio" className="form-label">
                    Bio
                  </label>
                  <textarea
                    className="form-control"
                    id="bio"
                    name="bio"
                    rows={3}
                    value={formData.bio}
                    onChange={handleChange}
                    disabled={!isEditing}
                  />
                </div>

                <div className="row mb-3">
                  <div className="col-md-6">
                    <label htmlFor="title" className="form-label">
                      Job Title
                    </label>
                    <input
                      type="text"
                      className="form-control"
                      id="title"
                      name="title"
                      value={formData.title}
                      onChange={handleChange}
                      disabled={!isEditing}
                    />
                  </div>
                  <div className="col-md-6">
                    <label htmlFor="company" className="form-label">
                      Company
                    </label>
                    <input
                      type="text"
                      className="form-control"
                      id="company"
                      name="company"
                      value={formData.company}
                      onChange={handleChange}
                      disabled={!isEditing}
                    />
                  </div>
                </div>

                <div className="mb-3">
                  <label htmlFor="location" className="form-label">
                    Location
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="location"
                    name="location"
                    value={formData.location}
                    onChange={handleChange}
                    disabled={!isEditing}
                  />
                </div>

                <hr className="my-4" />

                <h5 className="mb-3">Contact Information</h5>

                <div className="mb-3">
                  <label htmlFor="phone" className="form-label">
                    Phone
                  </label>
                  <input
                    type="tel"
                    className="form-control"
                    id="phone"
                    name="phone"
                    value={formData.phone}
                    onChange={handleChange}
                    disabled={!isEditing}
                  />
                </div>

                <div className="mb-3">
                  <label htmlFor="website" className="form-label">
                    Website
                  </label>
                  <input
                    type="url"
                    className="form-control"
                    id="website"
                    name="website"
                    value={formData.website}
                    onChange={handleChange}
                    disabled={!isEditing}
                    placeholder="https://..."
                  />
                </div>

                <hr className="my-4" />

                <h5 className="mb-3">Social Links</h5>

                <div className="mb-3">
                  <label htmlFor="twitter" className="form-label">
                    Twitter
                  </label>
                  <div className="input-group">
                    <span className="input-group-text">@</span>
                    <input
                      type="text"
                      className="form-control"
                      id="twitter"
                      name="twitter"
                      value={formData.twitter}
                      onChange={handleChange}
                      disabled={!isEditing}
                      placeholder="username"
                    />
                  </div>
                </div>

                <div className="mb-3">
                  <label htmlFor="linkedin" className="form-label">
                    LinkedIn
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="linkedin"
                    name="linkedin"
                    value={formData.linkedin}
                    onChange={handleChange}
                    disabled={!isEditing}
                    placeholder="username"
                  />
                </div>

                <div className="mb-3">
                  <label htmlFor="github" className="form-label">
                    GitHub
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="github"
                    name="github"
                    value={formData.github}
                    onChange={handleChange}
                    disabled={!isEditing}
                    placeholder="username"
                  />
                </div>

                {isEditing && (
                  <div className="d-flex gap-2 mt-4">
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={isSaving}
                    >
                      {isSaving ? (
                        <>
                          <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                          Saving...
                        </>
                      ) : (
                        'Save Changes'
                      )}
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => {
                        setIsEditing(false);
                        setError('');
                        setSuccess('');
                        // Reset form data to profile
                        if (profile) {
                          setFormData({
                            display_name: profile.display_name || '',
                            first_name: profile.first_name || '',
                            last_name: profile.last_name || '',
                            bio: profile.bio || '',
                            title: profile.title || '',
                            company: profile.company || '',
                            location: profile.location || '',
                            phone: profile.phone || '',
                            website: profile.website || '',
                            twitter: profile.twitter || '',
                            linkedin: profile.linkedin || '',
                            github: profile.github || '',
                          });
                        }
                      }}
                      disabled={isSaving}
                    >
                      Cancel
                    </button>
                  </div>
                )}
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
