package internal

import (
	"os"
	"log"
	"context"

	brevo "github.com/getbrevo/brevo-go/lib"
)

type NameEmail struct {
    name string
    email string
}

// Interfaz para abstraer la logica de enviar notificaciones de mail 
type emailSender interface {
	SendEmail(templateId int64, title string, message string, emails []NameEmail ) error
}

type emailService struct {
	apiClient	*brevo.APIClient
}

type mockEmailService struct {
}

func NewEmailService() emailSender {
	cfg := brevo.NewConfiguration()
	//Configure API key authorization: api-key
	cfg.AddDefaultHeader("api-key", os.Getenv("BREVO_KEY"))
	
	br := brevo.NewAPIClient(cfg)
    return &emailService{ apiClient: br, }
}


func (repo *emailService) SendEmail(templateId int64, title string, message string, emails []NameEmail ) error {
	for _, NameEmail := range emails {
		log.Printf("Sending email to %s %s", NameEmail.email, NameEmail.name )
		
		sendSmtpEmail := brevo.SendSmtpEmail{
			Sender: &brevo.SendSmtpEmailSender{
				Name:  "ClassConnect Not-reply",
				Email: os.Getenv("BREVO_EMAIL"),
			},
			To: []brevo.SendSmtpEmailTo{
				{
					Email: NameEmail.email,
					Name:  NameEmail.name,
				},
			},
			Subject:     title,
			TemplateId:  templateId,
			Params:  map[string]interface{}{
				"name":    NameEmail.name,      
				"title":   title,
				"message": message,
			},
		}	
		
		ctx := context.Background()
		_, _, err := repo.apiClient.TransactionalEmailsApi.SendTransacEmail(ctx, sendSmtpEmail)
		if err != nil {
			log.Println("Error sending email to ", NameEmail.email, err)
		}
	}

	return nil	
}

func NewMockEmailService() emailSender {	
    return &mockEmailService{}
}

func (repo *mockEmailService) SendEmail(templateId int64, title string, message string, emails []NameEmail ) error {
	return nil	
}


