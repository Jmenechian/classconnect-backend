FROM golang:1.21.0

WORKDIR /app

RUN apt-get update && apt-get install -y ca-certificates

COPY go.mod go.sum ./
RUN go mod download
 
COPY internal internal/
COPY authKey.json .
COPY cmd/prod/main.go .

RUN CGO_ENABLED=0 GOOS=linux go build -o ./docker-gs-ping

CMD ["./docker-gs-ping"]
