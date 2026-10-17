package tests

import (
	"bytes"
	"encoding/json"
	"ms-users/internal"
	"net/http"
	"os"
	"testing"

	"github.com/stretchr/testify/require"
)

var (
	baseURL string
	user    internal.User
	admin   internal.User
)

func init() {
	baseURL = "http://" + os.Getenv("HOST") + ":" + os.Getenv("PORT")

	user = internal.User{
		UID:   "1234",
		Token: "1234",
		NotifToken: "1234",
		Email: "testUser1@gmail.com",
	}

	admin = internal.User{
		UID:   "admin",
		Token: "admin",
		NotifToken: "admin",
		Email: "admin@gmail.com",
	}
}

func TestSignUpOK(t *testing.T) {
	// CREATE USER
	payload, err := json.Marshal(user)
	require.NoError(t, err)

	resp, err := http.Post(baseURL+"/auth/signup", "application/json", bytes.NewBuffer(payload))
	require.NoError(t, err)
	defer func() {
		_ = resp.Body.Close()
	}()

	require.Equal(t, http.StatusCreated, resp.StatusCode)

	var res struct {
		Data internal.AppUser `json:"data"`
	}

	err = json.NewDecoder(resp.Body).Decode(&res)
	require.NoError(t, err)

	require.Equal(t, user.UID, res.Data.UID)
	require.Equal(t, user.Email, res.Data.Email)
	require.NotEmpty(t, res.Data.Id)

	// CHECK CREATED USERs
	resp, err = http.Get(baseURL + "/users")
	require.NoError(t, err)
	defer func() {
		_ = resp.Body.Close()
	}()

	var res2 struct {
		Data []internal.AppUser `json:"data"`
	}

	err = json.NewDecoder(resp.Body).Decode(&res2)
	require.NoError(t, err)

	require.Len(t, res2.Data, 1)
	require.Equal(t, user.UID, res2.Data[0].UID)
	require.Equal(t, user.Email, res2.Data[0].Email)
	require.NotEmpty(t, res2.Data[0].Id)
}

func TestAdminSignUpOK(t *testing.T) {
	// CREATE ADMIN
	payload, err := json.Marshal(admin)
	require.NoError(t, err)

	resp, err := http.Post(baseURL+"/auth/admin/signup", "application/json", bytes.NewBuffer(payload))
	require.NoError(t, err)
	defer func() {
		_ = resp.Body.Close()
	}()

	require.Equal(t, http.StatusCreated, resp.StatusCode)

	var res struct {
		Data internal.User `json:"data"`
	}

	err = json.NewDecoder(resp.Body).Decode(&res)
	require.NoError(t, err)

	require.Equal(t, admin.UID, res.Data.UID)
	require.Equal(t, admin.Token, res.Data.Token)
	require.Equal(t, admin.Email, res.Data.Email)
	require.Equal(t, true, res.Data.IsAdmin)
	require.NotEmpty(t, res.Data.Id)

	// CHECK CREATED ADMINs
	resp, err = http.Get(baseURL + "/admins")
	require.NoError(t, err)
	defer func() {
		_ = resp.Body.Close()
	}()

	var res2 struct {
		Data []internal.User `json:"data"`
	}

	err = json.NewDecoder(resp.Body).Decode(&res2)
	require.NoError(t, err)

	require.Len(t, res2.Data, 1)
	require.Equal(t, admin.UID, res2.Data[0].UID)
	require.Equal(t, admin.Email, res2.Data[0].Email)
	require.NotEmpty(t, res2.Data[0].Id)
}

func TestSignInOK(t *testing.T) {
	signIn := func(endpoint string, u internal.User, expectedStatus int, description string) {
		payload, err := json.Marshal(u)
		require.NoError(t, err)

		resp, err := http.Post(baseURL+endpoint, "application/json", bytes.NewBuffer(payload))
		require.NoError(t, err)
		defer func() {
    		if err := resp.Body.Close(); err != nil {
        		t.Logf("warning: failed to close response body: %v", err)
    		}
		}()

		require.Equal(t, expectedStatus, resp.StatusCode, description)
	}

	// Checks different login cases 
	t.Run("User signs in as user", func(t *testing.T) {
		signIn("/auth/signin", user, http.StatusOK, "user should sign in successfully as user")
	})

	t.Run("Admin signs in as admin", func(t *testing.T) {
		signIn("/auth/admin/signin", admin, http.StatusOK, "admin should sign in successfully as admin")
	})

	t.Run("Admin signs in as user", func(t *testing.T) {
		signIn("/auth/signin", admin, http.StatusNotFound, "admin should not be found in /auth/signin")
	})

	t.Run("User signs in as admin", func(t *testing.T) {
		signIn("/auth/admin/signin", user, http.StatusNotFound, "user should not be found in /auth/admin/signin")
	})
}