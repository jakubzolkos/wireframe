# Authentication Debugging Guide

## What I Just Fixed:

1. ✅ **Removed all Supabase references**
2. ✅ **Fixed type mismatches** - `full_name` instead of `name`
3. ✅ **Fixed register function** - Now properly handles loading state
4. ✅ **Added console logging** for better debugging

## Current Status:

**Backend:** ✅ Working
```bash
# Test registration
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123456","full_name":"Test User"}'

# Response: {"id":"...","email":"test@example.com",...}
```

**Frontend Proxy:** ✅ Working
```bash
# Test via Vite proxy
curl -X POST http://localhost:3000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test2@example.com","password":"test123456","full_name":"Test User 2"}'

# Response: {"id":"...","email":"test2@example.com",...}
```

## How to Debug Sign Up Failures:

1. **Open Browser Console** (F12 → Console tab)

2. **Try to sign up** with:
   - Full Name: Test User
   - Email: test@example.com
   - Password: test123456

3. **Check console for logs:**
   ```
   Registering with: { email: '...', full_name: '...' }
   Registration successful: { id: '...', email: '...' }
   ```

4. **If you see errors:**
   - Look for `Auth error:` in console
   - Check Network tab (F12 → Network)
   - Filter for `register` request
   - Click on it to see Request/Response

## Common Issues:

### "Account exists" error
**Cause:** Email already registered in database

**Solution:** Either:
- Use a different email
- Or login with existing account
- Or delete from database:
  ```bash
  docker exec -it wireframe_db psql -U postgres -d wireframe -c "DELETE FROM users WHERE email='test@example.com';"
  ```

### "Sign up failed" with no details
**Cause:** Network error or CORS issue

**Solution:**
1. Check backend is running: `curl http://localhost:8080/api/v1/health`
2. Check proxy works: `curl http://localhost:3000/api/v1/health`
3. Restart frontend: `npm run dev`

### Request not reaching backend
**Cause:** Proxy misconfiguration

**Solution:**
1. Check `vite.config.ts` has proxy config
2. Check `.env` has `VITE_API_URL=http://localhost:8080`
3. Restart Vite dev server

## Testing Checklist:

- [ ] Backend running on port 8080
- [ ] Frontend running on port 3000
- [ ] Browser console open (F12)
- [ ] Try signup with NEW email
- [ ] Check console logs
- [ ] Check Network tab
- [ ] Try login after signup

## Quick Test Script:

Run this in your terminal to test the full flow:

```bash
# 1. Generate unique email
EMAIL="test$(date +%s)@example.com"

# 2. Register
echo "Registering: $EMAIL"
curl -X POST http://localhost:3000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"test123456\",\"full_name\":\"Test User\"}"

echo -e "\n\n"

# 3. Login
echo "Logging in: $EMAIL"
curl -X POST http://localhost:3000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$EMAIL&password=test123456"

echo -e "\n\nDone!"
```

## What to Share if Still Failing:

1. **Browser console output** (copy/paste the logs)
2. **Network tab screenshot** of the failed request
3. **Exact error message** shown in the toast
4. **Backend logs** from docker logs wireframe_backend

The console logs I added will show exactly where the failure is happening!
