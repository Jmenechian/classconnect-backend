package tests

type mockTokenService struct {}

func (repo *mockTokenService) VerifyToken(token string) (bool, error) {
	return true, nil
}
func (repo *mockTokenService) SendNotification(title string, message string, metadata map[string]string, tokens []string) error {
	return nil
}