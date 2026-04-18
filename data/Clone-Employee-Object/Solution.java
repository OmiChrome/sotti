import java.util.*;

class Address implements Cloneable {
    private String address;
    public Address(String address) { this.address = address; }
    public String getAddress() { return address; }
    public void setAddress(String address) { this.address = address; }
    @Override
    public Object clone() throws CloneNotSupportedException {
        return super.clone();
    }
}

class Department implements Cloneable {
    private String dept;
    public Department(String dept) { this.dept = dept; }
    public String getDept() { return dept; }
    public void setDept(String dept) { this.dept = dept; }
    @Override
    public Object clone() throws CloneNotSupportedException {
        return super.clone();
    }
}

class Person implements Cloneable {
    private String name;
    private Address addr;
    public Person(String name, Address addr) { this.name = name; this.addr = addr; }
    public String getName() { return name; }
    public Address getAddr() { return addr; }
    public void setAddr(Address addr) { this.addr = addr; }
    @Override
    public Object clone() throws CloneNotSupportedException {
        Person p = (Person) super.clone();
        p.addr = (Address) addr.clone();
        return p;
    }
}

class Employee extends Person implements Cloneable {
    private Department dept;
    public Employee(String name, Address addr, Department dept) {
        super(name, addr);
        this.dept = dept;
    }
    public Department getDept() { return dept; }
    public void setDept(Department dept) { this.dept = dept; }
    public void updateEmp(String newAddr, String newDept) {
        this.getAddr().setAddress(newAddr);
        this.dept.setDept(newDept);
    }
    @Override
    public Object clone() throws CloneNotSupportedException {
        Employee e = (Employee) super.clone();
        e.dept = (Department) dept.clone();
        return e;
    }
    @Override
    public String toString() {
        return getName() + " : " + getAddr().getAddress() + " : " + dept.getDept();
    }
}

public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        try {
            if (!sc.hasNextLine()) return;
            String name = sc.nextLine();
            if (!sc.hasNextLine()) return;
            String addr1 = sc.nextLine();
            if (!sc.hasNextLine()) return;
            String dept1 = sc.nextLine();
            if (!sc.hasNextLine()) return;
            String addr2 = sc.nextLine();
            if (!sc.hasNextLine()) return;
            String dept2 = sc.nextLine();

            Employee e1 = new Employee(name, new Address(addr1), new Department(dept1));
            Employee e2 = (Employee) e1.clone();
            e1.updateEmp(addr2, dept2);
            System.out.println(e1 + ", " + e2);
        } catch (Exception e) {
            // Silent catch
        }
    }
}