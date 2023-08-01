package wire

import "github.com/ZHJBOBO/multipath-quic-go/internal/protocol"

// AckRange is an ACK range
type AckRange struct {
	First protocol.PacketNumber
	Last  protocol.PacketNumber
}
