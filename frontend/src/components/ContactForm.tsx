import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { submitContact } from '../utils/api'
import styles from './ContactForm.module.css'

interface ContactFields {
  name: string
  email: string
  message: string
}

export default function ContactForm() {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ContactFields>({ defaultValues: { name: '', email: '', message: '' } })
  const [sent, setSent] = useState(false)
  const [error, setError] = useState(false)

  async function onSubmit(data: ContactFields) {
    setError(false)
    try {
      await submitContact(data)
      setSent(true)
      reset()
    } catch {
      setError(true)
    }
  }

  if (sent) {
    return (
      <p className={styles.success}>
        Thanks — your message has been received. We'll get back to you soon.
      </p>
    )
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit(onSubmit)} noValidate>
      <div className={styles.row}>
        <div className={styles.field}>
          <label>Name</label>
          <input {...register('name', { required: true })} placeholder="Your name" />
        </div>
        <div className={styles.field}>
          <label>Email</label>
          <input type="email" {...register('email', { required: true })} placeholder="you@example.com" />
        </div>
      </div>
      <div className={styles.field}>
        <label>Message</label>
        <textarea rows={4} {...register('message', { required: true })} placeholder="How can we help?" />
      </div>
      {(errors.name || errors.email || errors.message) && (
        <p className={styles.error}>Please fill in every field.</p>
      )}
      {error && <p className={styles.error}>Could not send your message — please try again.</p>}
      <button type="submit" className={styles.submitBtn} disabled={isSubmitting}>
        {isSubmitting ? 'Sending…' : 'Send message'}
      </button>
    </form>
  )
}
