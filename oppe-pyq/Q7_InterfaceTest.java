import java.util.*;

/**
 * QUESTION: Interfaces - Smartphone MobileDevice & Camera (Sep 2023 OPPE1, Section 1.4)
 * ============================================================================
 * Problem Statement:
 * A smartphone is both a mobile device and a camera. Complete the Java program
 * to print customized messages based on which role (mobile device or camera) is
 * given as input.
 *
 * - Interface MobileDevice has abstract method: String makeCall()
 * - Interface Camera has abstract method: String takePicture()
 * - Class Smartphone implements both MobileDevice and Camera:
 *     makeCall()      → returns "<name> makes a call"
 *     takePicture()   → returns "<name> takes a picture"
 *
 * Class InterfaceTest main():
 *   - Accepts 3 lines of input (type + name)
 *   - If type == "M": create MobileDevice using Smartphone, call makeCall()
 *   - If type == "C": create Camera using Smartphone, call takePicture()
 *   - Print all messages at end
 *
 * What you have to do:
 *   - Define interface MobileDevice
 *   - Define interface Camera
 *   - Define class Smartphone
 *
 * Test Cases:
 *   Input: M Samsung / C Canon / M iPhone
 *   Output: Samsung makes a call \n Canon takes a picture \n iPhone makes a call
 *
 *   Input: C Nikon / C Sony / C GoPro
 *   Output: Nikon takes a picture \n Sony takes a picture \n GoPro takes a picture
 *
 *   Input: C Huawei / M Huawei / M Huawei
 *   Output: Huawei takes a picture \n Huawei makes a call \n Huawei makes a call
 */

// DEFINE interface MobileDevice here
interface MobileDevice {
    String makeCall();
}

// DEFINE interface Camera here
interface Camera {
    String takePicture();
}

// DEFINE class Smartphone here
class Smartphone implements MobileDevice, Camera {
    private String name;

    Smartphone(String n){name=n;}
    public String makeCall(){return name+" makes a call";}
    public String takePicture(){return name+" takes a picture";}
}

class Q7_InterfaceTest {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        ArrayList<String> messagesList = new ArrayList<>();
        for (int i = 0; i < 3; i++) {
            String type = sc.next();
            if (type.equals("M")) {
                MobileDevice m = new Smartphone(sc.next());
                messagesList.add(m.makeCall());
            } else if (type.equals("C")) {
                Camera c = new Smartphone(sc.next());
                messagesList.add(c.takePicture());
            }
        }
        for (String s : messagesList) {
            System.out.println(s);
        }
        sc.close();
    }
}
