package main

import (
	"fmt"
	"github.com/ZHJBOBO/multipath-quic-go"
	"github.com/ZHJBOBO/multipath-quic-go/example/sample/config"
	"github.com/ZHJBOBO/multipath-quic-go/example/sample/utils"
	"io"
	"log"
	"os"
	"strconv"
	"strings"
	"time"
)

func main() {

	mp_flag, _ := strconv.ParseBool(os.Args[1])

	quicConfig := &quic.Config{
		CreatePaths: mp_flag,
	}

	recv_perf := "D:\\testdata\\zcp_server_recv_perf_" + os.Args[1] + ".csv"
	fmt.Println(recv_perf)

	addr := os.Args[2] + ":" + config.PORT

	fmt.Println("Attaching to: ", addr)
	listener, err := quic.ListenAddr(addr, utils.GenerateTLSConfig(), quicConfig)
	utils.HandleError(err)

	fmt.Println("Server started! Waiting for streams from client...")

	if err != nil {
		log.Fatalln(err)
	}
	for {
		sess, err := listener.Accept()

		stream, err := sess.AcceptStream()
		utils.HandleError(err)

		fmt.Println("stream created: ", stream.StreamID())

		if err != nil {
			fmt.Printf("encounter error when accept: %s\n", err)
			continue
		}
		go handleQuicSession(stream, recv_perf)
	}
}

func handleQuicSession(stream quic.Stream, recv_perf string) {

	defer stream.Close()
	fmt.Println("Connected to server, start receiving the file name and file size")
	bufferFileName := make([]byte, 64)
	bufferFileSize := make([]byte, 10)

	stream.Read(bufferFileSize)
	fileSize, _ := strconv.ParseInt(strings.Trim(string(bufferFileSize), ":"), 10, 64)

	fmt.Println("file size received: ", fileSize)

	stream.Read(bufferFileName)
	fileName := strings.Trim(string(bufferFileName), ":")

	fmt.Println("file name received: ", fileName)

	//os.Mkdir("/tmp/serv_test", 0777)
	newFile, err := os.Create("D:\\testdata\\" + fileName)
	utils.HandleError(err)

	f_perf, err := os.Create(recv_perf)
	if err != nil {
		fmt.Println(err)
	}

	//defer newFile.Close()
	var receivedBytes int64
	start := time.Now()

	for {
		if (fileSize - receivedBytes) < config.BUFFERSIZE {
			// fmt.Println("\nlast chunk of file.")

			now := time.Now()               // current local time
			nanosec_start := now.UnixNano() // number of nanoseconds since January 1, 1970 UTC
			recv, err := io.CopyN(newFile, stream, (fileSize - receivedBytes))
			utils.HandleError(err)

			stream.Read(make([]byte, (receivedBytes+config.BUFFERSIZE)-fileSize))
			receivedBytes += recv

			now = time.Now()              // current local time
			nanosec_end := now.UnixNano() // number of nanoseconds since January 1, 1970 UTC

			fmt.Fprintf(f_perf, "%d,%d,%d\n", (nanosec_end - nanosec_start), receivedBytes, fileSize)
			break
		}
		//_ := LimitReader(stream, config.BUFFERSIZE)

		now := time.Now()               // current local time
		nanosec_start := now.UnixNano() // number of nanoseconds since January 1, 1970 UTC
		_, err := io.CopyN(newFile, stream, config.BUFFERSIZE)
		utils.HandleError(err)

		receivedBytes += config.BUFFERSIZE

		now = time.Now()              // current local time
		nanosec_end := now.UnixNano() // number of nanoseconds since January 1, 1970 UTC
		fmt.Fprintf(f_perf, "%d,%d,%d\n", (nanosec_end - nanosec_start), receivedBytes, fileSize)
	}
	elapsed := time.Since(start)
	fmt.Println("\nTransfer took: ", elapsed)

	//time.Sleep(2 * time.Second)
	stream.Close()
	stream.Close()
	newFile.Close()
	fmt.Println("\n\nReceived file completely!")
}
