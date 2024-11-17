import React, { useState, useEffect } from 'react';
import { 
  TextField, 
  Button, 
  Box, 
  Typography, 
  MenuItem, 
  Select, 
  InputLabel, 
  FormControl,
  Paper,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import { Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import moment from 'moment-timezone';

const skillsList = [
  'JavaScript', 'Python', 'Java', 'C#', 'C++', 'Go', 'Ruby', 'React', 
  'Angular', 'Vue.js', 'Node.js', 'Django', 'Flask', 'Spring', 'Docker',
  'Kubernetes', 'AWS', 'Azure', 'GCP', 'MongoDB', 'PostgreSQL', 'MySQL'
];

interface Project {
  title: string;
  description: string;
}

interface Experience {
  company: string;
  years: number;
}

interface Certificate {
  title: string;
  link: string;
  completion_date: string;
}

const Profile = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();
  
  const [profileData, setProfileData] = useState({
    bio: '',
    personal_website: '',
    linkedin: '',
    years_of_experience: 0,
    skills: [] as string[],
    projects: [] as Project[],
    experiences: [] as Experience[],
    timezone: moment.tz.guess(),
    education: [] as string[],
    certificates: [] as Certificate[],
    availability: '',
    onboarding_completed: false
  });

  const [pfpFile, setPfpFile] = useState<File | null>(null);
  const [pfpPreview, setPfpPreview] = useState<string>('');
  const [openDialog, setOpenDialog] = useState('');
  const [tempItem, setTempItem] = useState<any>({});

  useEffect(() => {
    if (user) {
      axios.get('/api/user/profile')
        .then(response => {
          setProfileData(response.data.profile || {});
          if (response.data.profile?.pfp_url) {
            setPfpPreview(response.data.profile.pfp_url);
          }
        })
        .catch(() => navigate('/login'));
    } else {
      navigate('/login');
    }
  }, [user, navigate]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setProfileData({ ...profileData, [e.target.name]: e.target.value });
  };

  const handleSkillsChange = (event: any) => {
    setProfileData({ ...profileData, skills: event.target.value as string[] });
  };

  const handlePfpChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setPfpFile(file);
      setPfpPreview(URL.createObjectURL(file));
    }
  };

  const handlePfpUpload = async () => {
    if (pfpFile) {
      const formData = new FormData();
      formData.append('file', pfpFile);
      try {
        await axios.post('/api/user/profile/picture', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        alert(t('profilePictureUpdateSuccess'));
      } catch (error) {
        alert(t('profilePictureUpdateError'));
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await axios.put('/api/user/profile', {
        ...profileData,
        onboarding_completed: true
      });
      alert(t('profileUpdateSuccess'));
    } catch (error) {
      alert(t('profileUpdateError'));
    }
  };

  const handleAddItem = (type: string) => {
    setOpenDialog(type);
    setTempItem({});
  };

  const handleSaveItem = () => {
    switch (openDialog) {
      case 'project':
        setProfileData({
          ...profileData,
          projects: [...profileData.projects, tempItem]
        });
        break;
      case 'experience':
        setProfileData({
          ...profileData,
          experiences: [...profileData.experiences, tempItem]
        });
        break;
      case 'education':
        setProfileData({
          ...profileData,
          education: [...profileData.education, tempItem]
        });
        break;
      case 'certificate':
        setProfileData({
          ...profileData,
          certificates: [...profileData.certificates, tempItem]
        });
        break;
    }
    setOpenDialog('');
    setTempItem({});
  };

  return (
    <Box component={Paper} sx={{ p: 3, m: 3 }}>
      <Typography variant="h4" gutterBottom>
        {t('profile.title')}
      </Typography>

      <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {/* Profile Picture Section */}
        <Box sx={{ mb: 3, textAlign: 'center' }}>
          <Box
            component="img"
            src={pfpPreview || '/default-avatar.png'}
            alt="Profile"
            sx={{ width: 150, height: 150, borderRadius: '50%', mb: 2 }}
          />
          <input
            accept="image/*"
            type="file"
            onChange={handlePfpChange}
            style={{ display: 'none' }}
            id="pfp-upload"
          />
          <label htmlFor="pfp-upload">
            <Button variant="contained" component="span">
              {t('profile.uploadPicture')}
            </Button>
          </label>
          {pfpFile && (
            <Button onClick={handlePfpUpload} sx={{ ml: 2 }}>
              {t('profile.savePicture')}
            </Button>
          )}
        </Box>

        {/* Basic Information */}
        <TextField
          name="bio"
          label={t('profile.bio')}
          multiline
          rows={4}
          value={profileData.bio}
          onChange={handleChange}
        />

        <TextField
          name="personal_website"
          label={t('profile.personalWebsite')}
          value={profileData.personal_website}
          onChange={handleChange}
        />

        <TextField
          name="linkedin"
          label={t('profile.linkedin')}
          value={profileData.linkedin}
          onChange={handleChange}
        />

        <TextField
          name="years_of_experience"
          label={t('profile.yearsOfExperience')}
          type="number"
          value={profileData.years_of_experience}
          onChange={handleChange}
        />

        {/* Skills Selection */}
        <FormControl>
          <InputLabel>{t('profile.skills')}</InputLabel>
          <Select
            multiple
            value={profileData.skills}
            onChange={handleSkillsChange}
            renderValue={(selected) => (selected as string[]).join(', ')}
          >
            {skillsList.map((skill) => (
              <MenuItem key={skill} value={skill}>
                {skill}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* Projects Section */}
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">{t('profile.projects')}</Typography>
            <IconButton onClick={() => handleAddItem('project')}>
              <AddIcon />
            </IconButton>
          </Box>
          <List>
            {profileData.projects.map((project, index) => (
              <ListItem key={index}>
                <ListItemText
                  primary={project.title}
                  secondary={project.description}
                />
                <ListItemSecondaryAction>
                  <IconButton onClick={() => {
                    setProfileData({
                      ...profileData,
                      projects: profileData.projects.filter((_, i) => i !== index)
                    });
                  }}>
                    <DeleteIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </Box>

        {/* Similar sections for experiences, education, and certificates */}
        {/* ... */}

        <FormControl>
          <InputLabel>{t('profile.timezone')}</InputLabel>
          <Select
            value={profileData.timezone}
            onChange={(e) => setProfileData({ ...profileData, timezone: e.target.value as string })}
          >
            {moment.tz.names().map((tz) => (
              <MenuItem key={tz} value={tz}>
                {tz} ({moment.tz(tz).format('Z')})
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <TextField
          name="availability"
          label={t('profile.availability')}
          value={profileData.availability}
          onChange={handleChange}
        />

        <Button type="submit" variant="contained" sx={{ mt: 3 }}>
          {t('profile.saveChanges')}
        </Button>
      </Box>

      {/* Dialogs for adding items */}
      <Dialog open={Boolean(openDialog)} onClose={() => setOpenDialog('')}>
        <DialogTitle>{t(`profile.add${openDialog}`)}</DialogTitle>
        <DialogContent>
          {/* Dialog content varies based on openDialog type */}
          {/* ... */}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog('')}>{t('common.cancel')}</Button>
          <Button onClick={handleSaveItem}>{t('common.save')}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Profile;