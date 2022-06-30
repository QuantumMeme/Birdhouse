#include <bcm2835.h>
#include <stdio.h>

int main(int argc, char **argv)
{
    if(!bcm2835_init())
    {
        printf("could not resolve bcm2835\n");
        return 1;
    }
    if(!bcm2835_spi_begin())
    {
        printf("bcm2835_spi_begin failed. Are you running as root??\n");
    }
    bcm2835_spi_setBitOrder(BCM2835_SPI_BIT_ORDER_MSBFIRST);
    bcm2835_spi_setDataMode(BCM2835_SPI_MODE0);
    bcm2835_spi_setClockDivider(BCM2835_SPI_CLOCK_DIVIDER_64);
    bcm2835_spi_chipSelect(BCM2835_SPI_CS0);
    bcm2835_spi_setChipSelectPolarity(BCM2835_SPI_CS0, LOW);

    uint8_t mosi[10]={0x60, 0x00};
    uint8_t miso[10] = {NULL};
    bcm2835_spi_transfernb(mosi,miso,2);
    printf("%04x\n", miso[1]+((miso[0]&3)<<8));

    bcm2835_spi_end();
    bcm2835_close();
    return 0;
}