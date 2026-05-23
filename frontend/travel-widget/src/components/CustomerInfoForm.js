import React, { useState } from 'react';
import '../App.css';

const CustomerInfoForm = ({ onSubmit, onClose }) => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    budget: ''
  });

  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validateName = (name) => {
    const nameRegex = /^[a-zA-Z\s]{2,50}$/;
    if (!name.trim()) return 'Name is required';
    if (!nameRegex.test(name.trim())) return 'Name must contain only letters and spaces (2-50 characters)';
    return '';
  };

  const validateEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email.trim()) return 'Email is required';
    if (!emailRegex.test(email.trim())) return 'Please enter a valid email address';
    return '';
  };

  const validatePhone = (phone) => {
    const phoneRegex = /^\+\d{1,3}[-.\s]?\d{1,14}([-.\s]?\d{1,13})*$/;
    const cleanPhone = phone.replace(/\s+/g, '');
    
    if (!cleanPhone) return 'Phone number is required';
    if (!phoneRegex.test(cleanPhone)) return 'Please enter a valid international phone number (+country code)';
    if (cleanPhone.length < 8 || cleanPhone.length > 20) return 'Phone number must be 8-20 characters';
    return '';
  };

  const validateBudget = (budget) => {
    const budgetRegex = /^\$?\d{1,6}(\.\d{1,2})?$/;
    const numericBudget = budget.replace(/[$,\s]/g, '');
    
    if (!budget.trim()) return 'Budget is required';
    if (!budgetRegex.test(budget.replace(/,/g, ''))) return 'Please enter a valid budget amount (e.g., $1000, 1500.50)';
    
    const amount = parseFloat(numericBudget);
    if (amount < 100) return 'Minimum budget is $100';
    if (amount > 999999) return 'Maximum budget is $999,999';
    return '';
  };

  const formatPhone = (value) => {
    let formatted = value.replace(/[^\d+\-.\s]/g, '');
    if (formatted && !formatted.startsWith('+')) {
      formatted = '+' + formatted;
    }
    return formatted;
  };

  const formatBudget = (value) => {
    let formatted = value.replace(/[^\d.$]/g, '');
    
    if (formatted && !formatted.startsWith('$')) {
      formatted = '$' + formatted;
    }
    
    const parts = formatted.split('.');
    if (parts.length > 2) {
      formatted = parts[0] + '.' + parts[1];
    }
    if (parts[1] && parts[1].length > 2) {
      formatted = parts[0] + '.' + parts[1].substring(0, 2);
    }
    
    return formatted;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    let formattedValue = value;

    switch (name) {
      case 'name':
        formattedValue = value.replace(/[^a-zA-Z\s]/g, '');
        break;
      case 'phone':
        formattedValue = formatPhone(value);
        break;
      case 'budget':
        formattedValue = formatBudget(value);
        break;
      default:
        break;
    }

    setFormData({
      ...formData,
      [name]: formattedValue
    });

    let error = '';
    switch (name) {
      case 'name':
        error = validateName(formattedValue);
        break;
      case 'email':
        error = validateEmail(formattedValue);
        break;
      case 'phone':
        error = validatePhone(formattedValue);
        break;
      case 'budget':
        error = validateBudget(formattedValue);
        break;
      default:
        break;
    }

    setErrors({
      ...errors,
      [name]: error
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    const newErrors = {
      name: validateName(formData.name),
      email: validateEmail(formData.email),
      phone: validatePhone(formData.phone),
      budget: validateBudget(formData.budget)
    };

    setErrors(newErrors);

    const hasErrors = Object.values(newErrors).some(error => error !== '');
    if (hasErrors) {
      setIsSubmitting(false);
      return;
    }

    const cleanedData = {
      name: formData.name.trim(),
      email: formData.email.trim().toLowerCase(),
      phone: formData.phone.replace(/\s+/g, ''), 
      budget: formData.budget.replace(/[$,]/g, '') 
    };

    onSubmit(cleanedData);
    setIsSubmitting(false);
  };

  const isFormValid = () => {
    return Object.values(formData).every(value => value.trim() !== '') &&
           Object.values(errors).every(error => error === '');
  };

  return (
    <div className="customer-form-overlay">
      <div className="customer-form-container">
        <h3>Please enter your information to plan your trip ✈️</h3>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <input
              type="text"
              name="name"
              placeholder="Full Name (e.g., John Smith)"
              value={formData.name}
              onChange={handleChange}
              required
              maxLength="50"
              className={errors.name ? 'error' : ''}
            />
            {errors.name && <span className="error-message">{errors.name}</span>}
          </div>

          <div className="form-group">
            <input
              type="email"
              name="email"
              placeholder="Email (e.g., john@example.com)"
              value={formData.email}
              onChange={handleChange}
              required
              className={errors.email ? 'error' : ''}
            />
            {errors.email && <span className="error-message">{errors.email}</span>}
          </div>

          <div className="form-group">
            <input
              type="tel"
              name="phone"
              placeholder="Phone (+1234567890)"
              value={formData.phone}
              onChange={handleChange}
              required
              className={errors.phone ? 'error' : ''}
            />
            {errors.phone && <span className="error-message">{errors.phone}</span>}
          </div>

          <div className="form-group">
            <input
              type="text"
              name="budget"
              placeholder="Budget ($1000)"
              value={formData.budget}
              onChange={handleChange}
              required
              className={errors.budget ? 'error' : ''}
            />
            {errors.budget && <span className="error-message">{errors.budget}</span>}
          </div>

          <div className="form-buttons">
            <button 
              type="submit" 
              disabled={!isFormValid() || isSubmitting}
              className={isFormValid() ? 'valid' : 'invalid'}
            >
              {isSubmitting ? 'Processing...' : 'Get travel plans ✈️'}
            </button>
            <button type="button" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CustomerInfoForm;