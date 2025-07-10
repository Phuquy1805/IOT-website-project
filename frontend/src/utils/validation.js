/**
 * Username must be 3–20 characters, letters, numbers or underscore only.
 */
export function validateUsername(username) {
  const re = /^[A-Za-z0-9_]{3,20}$/;
  return re.test(username);
}

/**
 * Password must be at least 8 characters, include at least:
 *  - one letter
 *  - one number
 *  - one special character (anything other than letter/number)
 */
export function validatePassword(password) {
  const re = /^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z\d]).{8,}$/;
  return re.test(password);
}